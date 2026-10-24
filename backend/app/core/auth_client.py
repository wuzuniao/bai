"""
auth 服务客户端（bai → auth 服务间通信封装，面向对象：AuthClient 类 + 模块级单例）
--------------------------------------------------------------------------
数据库彻底拆分后，bai 不直连用户库（用户库归 auth 服务专属），
用户相关信息一律经本客户端调用 auth 服务的 /internal/* 接口获取
（HTTPS 域名传输 + X-Service-Token）。

职责清单：
1. JWKS 公钥管理：启动/未知 kid 时拉取 /.well-known/jwks.json，
   磁盘（backend/.jwks_cache.json）+ 内存双缓存；auth 不可达时用上次缓存继续验签
2. 令牌撤销增量同步：GET /internal/revocations?since=<水位>（后台每
   REVOCATION_SYNC_INTERVAL_SECONDS 秒拉取；进程重启/首次运行回填 3 天
   = access_token TTL 上限），每请求经 is_revoked(user_id, iat) 本地比对，
   零网络调用
3. （已下线）账号删除上报/合并协同：账号别名与合并改造（2026-10-01）后，账号合并与
   删号标记完全收敛在 auth 内部，业务库残留数据永久接受，撤销增量按本项目认识的
   identity id 比对

说明：邮箱/openid 查询依赖具体业务数据，待 bai 业务功能落地后按需扩展。

性能原则（与 yao 一致）：access_token 有效期内纯本地 RS256 验签，
不逐请求调用 auth；撤销窗口 ≈ 同步间隔（默认 300 秒，.env 可调）。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from ..utils.logger import logger
from ..utils.timezone import TimezoneUtil
from .config import settings


class AuthClient:
    """auth 服务间通信客户端（JWKS 公钥管理 / 撤销增量同步 / 服务间写调用）"""

    # JWKS 磁盘缓存路径（backend/.jwks_cache.json，已加入 .gitignore）
    JWKS_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / ".jwks_cache.json"

    # 撤销增量首轮回填窗口（天）= access_token 最大 TTL（重启后补齐漏拉的撤销记录）
    REVOCATION_BACKFILL_DAYS: int = 3

    # HTTP 调用超时（秒）
    HTTP_TIMEOUT: float = 10.0

    def __init__(self) -> None:
        # 内存缓存：kid -> RSAPublicKey 公钥对象
        self._jwks_keys: dict[str, Any] = {}
        # 撤销同步状态（进程内存）：
        # - _revocations：{user_id: 撤销时刻 Unix 时间戳}（本地比对 iat 用）
        # - _revocation_watermark：增量拉取水位（auth 返回的服务器当前时间 ISO 字符串）
        self._revocations: dict[int, float] = {}
        self._revocation_watermark: str | None = None

    # ==================== HTTP 基础 ====================

    @staticmethod
    def _auth_url(path: str) -> str:
        """拼接 auth 服务完整地址（代码零硬编码地址，全部走 .env 配置）"""
        return f"{settings.AUTH_BASE_URL.rstrip('/')}{path}"

    @staticmethod
    def _service_headers() -> dict[str, str]:
        """服务间通信请求头（X-Service-Token，与 auth 服务 .env 配置相同值）"""
        return {"X-Service-Token": settings.AUTH_SERVICE_TOKEN}

    async def _get_json(self, path: str, params: dict | None = None) -> dict:
        """调用 auth 服务 GET 接口并返回 JSON（非 2xx 抛异常由调用方降级处理）"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._auth_url(path),
                params=params,
                headers=self._service_headers(),
                timeout=self.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()

    async def _post_json(self, path: str, json_body: dict | None = None) -> dict:
        """调用 auth 服务 POST 接口并返回 JSON（非 2xx 抛异常由调用方处理）"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._auth_url(path),
                json=json_body or {},
                headers=self._service_headers(),
                timeout=self.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()

    # ==================== JWKS 公钥管理 ====================

    def _load_jwks_from_disk(self) -> bool:
        """
        从磁盘缓存加载 JWKS 公钥（auth 不可达时的验签兜底；公钥非机密）
        :return: 是否加载成功
        """
        try:
            if not self.JWKS_CACHE_PATH.exists():
                return False
            data = json.loads(self.JWKS_CACHE_PATH.read_text(encoding="utf-8"))
            keys = {}
            for jwk in data.get("keys", []):
                keys[jwk["kid"]] = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            if not keys:
                return False
            self._jwks_keys = keys
            return True
        except Exception as e:
            logger.warning(f"加载 JWKS 磁盘缓存失败：{e}")
            return False

    def _save_jwks_to_disk(self, data: dict) -> None:
        """将 JWKS 原始响应写入磁盘缓存（写入失败仅告警，不影响内存缓存）"""
        try:
            self.JWKS_CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"写入 JWKS 磁盘缓存失败：{e}")

    async def fetch_jwks(self) -> bool:
        """
        拉取 auth 服务 JWKS 公钥集，更新内存 + 磁盘双缓存
        - 进程启动时调用一次；遇未知 kid 时重拉（支持 auth 密钥轮换）
        :return: 是否拉取成功
        """
        try:
            data = await self._get_json("/.well-known/jwks.json")
        except Exception as e:
            logger.warning(f"拉取 JWKS 失败：{e}")
            # 拉取失败：尝试磁盘缓存兜底（auth 不可达时用上次缓存公钥继续验签）
            if not self._jwks_keys:
                if self._load_jwks_from_disk():
                    logger.info("已回退到 JWKS 磁盘缓存继续验签")
                    return True
            return False
        keys = {}
        for jwk in data.get("keys", []):
            try:
                keys[jwk["kid"]] = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            except Exception as e:
                logger.warning(f"JWKS 公钥解析失败 kid={jwk.get('kid')}：{e}")
        if not keys:
            logger.warning("JWKS 响应中无有效公钥")
            return False
        self._jwks_keys = keys
        self._save_jwks_to_disk(data)
        logger.info(f"JWKS 已更新（{len(keys)} 把公钥）")
        return True

    def get_public_key(self, kid: str | None) -> RSAPublicKey | None:
        """
        按 kid 获取公钥（内存缓存命中）
        :param kid: JWT header 中的 key id
        :return: 公钥对象；内存未命中时尝试磁盘缓存；仍无则返回 None（调用方触发重拉）
        """
        if kid and kid in self._jwks_keys:
            return self._jwks_keys[kid]
        if not self._jwks_keys:
            self._load_jwks_from_disk()
            return self._jwks_keys.get(kid) if kid else None
        return None

    # ==================== 令牌撤销增量同步 ====================

    @staticmethod
    def _parse_shanghai_iso(value: str) -> float | None:
        """
        解析 auth 返回的 ISO 时间字符串为 Unix 时间戳
        - 带时区（Z / +08:00）按其时区；无时区按上海时区（与 auth 侧约定一致）
        """
        try:
            dt = datetime.fromisoformat(value.strip())
        except (ValueError, AttributeError):
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TimezoneUtil.SHANGHAI_TZ)
        return dt.timestamp()

    async def pull_revocations(self) -> int:
        """
        拉取令牌撤销增量并合并本地状态（后台循环每 REVOCATION_SYNC_INTERVAL_SECONDS 秒调用）
        - 首次运行/进程重启：水位回填 3 天（= access_token TTL 上限，补齐宕机期间漏拉记录）
        - 拉取失败保留旧水位，下一轮重试（容忍 auth 短暂不可达）
        :return: 本轮新增/更新的撤销记录数
        """
        if self._revocation_watermark is None:
            since = (TimezoneUtil.now() - timedelta(days=self.REVOCATION_BACKFILL_DAYS)).isoformat()
        else:
            since = self._revocation_watermark
        try:
            data = await self._get_json("/internal/revocations", params={"since": since})
        except Exception as e:
            logger.warning(f"拉取令牌撤销增量失败：{e}")
            return 0

        payload = data.get("data") or {}
        added = 0
        for item in payload.get("items", []):
            user_id = item.get("user_id")
            ts = self._parse_shanghai_iso(item.get("revoked_at", ""))
            if user_id is None or ts is None:
                continue
            # 同一用户多次撤销取最新时刻
            if ts > self._revocations.get(user_id, 0.0):
                self._revocations[user_id] = ts
                added += 1
        watermark = payload.get("watermark")
        if watermark:
            self._revocation_watermark = watermark
        return added

    def is_revoked(self, user_id: int, iat: int) -> bool:
        """
        本地比对令牌是否已被撤销（每请求零网络调用）
        :param user_id: 用户ID（令牌 sub）
        :param iat: 令牌签发时间 Unix 时间戳
        :return: iat 早于该用户最新撤销时刻 → 已撤销
        """
        revoked_before = self._revocations.get(user_id)
        return revoked_before is not None and iat < revoked_before

    # ==================== 用户信息查询（服务间读调用） ====================

    async def get_user_info(self, user_id: int) -> dict:
        """
        查询用户基本信息（GET /internal/users/{id}；入参别名解析，资料取属主行）
        :return: auth 响应 data（{id, username, email, status, roles}）
        :raises RuntimeError: auth 业务错误或网络异常（由调用方决定降级行为）
        """
        data = await self._get_json(f"/internal/users/{user_id}")
        if data.get("code") != 0:
            raise RuntimeError(f"auth 查询用户信息失败：{data.get('msg', '未知错误')}")
        return data.get("data") or {}

    # ==================== 会员购买授权（服务间写调用） ====================

    async def grant_membership(
        self,
        user_id: int,
        role_code: str,
        duration_days: int,
        order_no: str,
        amount: float,
        currency: str,
    ) -> dict:
        """
        请求 auth 服务授予会员角色（金币支付成功后调用；POST /internal/membership/grant）
        - 计价与时长由本项目服务端下发（前端不可传价格），order_no 幂等防重放
        - auth 侧续费顺延、落账购买记录并扇出令牌撤销（本项目撤销同步拉取后
          旧令牌 401，客户端静默刷新即携带新角色）
        :return: auth 响应 data（{duplicated, role_code, expires_at}）
        :raises RuntimeError: auth 业务错误（code != 0）或网络异常（由调用方补偿退款）
        """
        data = await self._post_json(
            "/internal/membership/grant",
            {
                "user_id": user_id,
                "role_code": role_code,
                "duration_days": duration_days,
                "client_id": settings.AUTH_CLIENT_ID,
                "order_no": order_no,
                "amount": amount,
                "currency": currency,
            },
        )
        if data.get("code") != 0:
            raise RuntimeError(f"auth 授权失败：{data.get('msg', '未知错误')}")
        return data.get("data") or {}


# 模块级单例（全项目经 auth_client 使用）
auth_client = AuthClient()
