"""
腾讯云 COS 对象存储服务（书籍文件云端同步，面向对象：CosService 类 + 模块级单例）
--------------------------------------------------------------------------------
职责：后端持有永久密钥，经 STS GetFederationToken 换取「按用户目录隔离」的临时密钥，
再签发 COS 预签名 URL 下发前端直传/下载——永久密钥与临时凭证均不出后端。

安全模型：
1. Policy 最小授权：action 仅 PutObject/GetObject，resource 精确限定到
   qcs::cos:<region>:uid/<appid>:<桶>/<用户 id>/* 六段式（桶名式；实测 STS 文档示例的
   prefix// 前缀式会被 COS 判 AccessDenied）；
2. 用户目录 = 业务用户 id（JWT sub：终身不变、全项目唯一，杜绝前端传入伪造目录；
   2026-10-24 起由 auth 用户名切换，旧用户名目录残留由运维经 COS 控制台手动清理）；
3. 对象 key 规则：{用户 id}/{书名}.{扩展名}（书名即对象名，桶内按用户 id 分目录）；
4. 临时凭证按用户目录内存缓存复用（临近过期自动重取，避免限频）。

职责边界：桶列举（GetBucket）与对象删除（DeleteObject）由本服务持永久密钥服务端直调，
前端拿不到列举能力；上传/下载走预签名 URL 前端直传直取。删书勾选「同时删除云端数据」
时经 POST /cos/delete 同步删除云端对象（幂等 204）。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree

import httpx

from ..core.config import settings
from ..core.exceptions import BusinessError
from ..utils.logger import logger


class CosService:
    """COS 云同步（STS 临时凭证换取 / 预签名 URL 签发 / 云端清单查询与对象删除）"""

    # 会员角色编码（与 reward_service.MAKEUP_ROLE_CODES 同口径：令牌 roles 本地比对，
    # 不实时查 auth；黑铁及以上可使用云端同步）
    MEMBER_ROLE_CODES: list[str] = ["iron", "bronze", "silver", "gold", "admin"]

    # 凭证缓存提前失效余量（秒）：临近过期即重取，保证随后签出的 URL 全程有效
    CRED_REFRESH_MARGIN: int = 120

    # 预签名 URL 有效期（秒；临时凭证默认 1800 秒，URL 须短于凭证剩余有效期）
    PRESIGN_TTL: int = 600

    # 目录清单单次拉取上限
    LIST_MAX_KEYS: int = 1000

    # HTTP 调用超时（秒）
    HTTP_TIMEOUT: float = 10.0

    def __init__(self) -> None:
        # 临时凭证缓存：user_dir -> (credentials, expired_unix_ts)
        self._cred_cache: dict[str, tuple[dict[str, str], int]] = {}

    # ==================== 校验与目录 ====================

    @classmethod
    def is_member(cls, payload: dict) -> bool:
        """令牌 roles 本地比对：黑铁及以上（含管理员）为会员"""
        roles = [str(r) for r in (payload.get("roles") or [])]
        return any(role in cls.MEMBER_ROLE_CODES for role in roles)

    @staticmethod
    def sanitize_segment(value: str) -> str:
        """目录/文件名段清洗：剥离路径分隔符与控制字符（保持桶内单层目录约定）"""
        cleaned = "".join(
            ch for ch in (value or "").strip() if ch.isprintable() and ch not in "/\\"
        )
        return cleaned.strip()

    @staticmethod
    def object_key(user_dir: str, title: str, ext: str) -> str:
        """对象 key：{用户 id}/{书名}.{扩展名}"""
        return f"{user_dir}/{CosService.sanitize_segment(title)}.{ext}"

    async def get_user_dir(self, user_id: int) -> str:
        """
        解析用户独立目录（= 业务用户 id，即 JWT sub：终身不变、全项目唯一，
        杜绝前端伪造目录；不再依赖 auth 服务间解析与用户名存在性）
        """
        return str(user_id)

    def _require_config(self) -> None:
        if not (settings.COS_SECRET_ID and settings.COS_SECRET_KEY and settings.COS_BUCKET):
            raise RuntimeError("COS 配置缺失（backend/.env 未配置 COS_* 项）")

    # ==================== STS 临时凭证（TC3-HMAC-SHA256 签名调用） ====================

    def _build_policy(self, user_dir: str) -> str:
        """按用户目录构造最小授权 Policy（JSON 字符串，不含 principal）"""
        bucket = settings.COS_BUCKET
        region = settings.COS_REGION
        appid = settings.COS_APPID
        # 资源六段式采用「桶名式」写法（qcs::cos:<region>:uid/<appid>:<桶>/<目录>/*）；
        # 实测 STS 文档示例的 prefix//<appid>/<桶>/ 式会被 COS 判 AccessDenied。
        # 不授 GetBucket/ListBucket：桶列举不支持目录级资源限定，清单由本服务持
        # 永久密钥代查（见 list_objects），前端永远拿不到跨目录列举能力
        resource = f"qcs::cos:{region}:uid/{appid}:{bucket}/{user_dir}/*"
        policy = {
            "version": "2.0",
            "statement": [
                {
                    "effect": "allow",
                    "action": [
                        "name/cos:PutObject",
                        "name/cos:GetObject",
                    ],
                    "resource": [resource],
                }
            ],
        }
        return json.dumps(policy, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def issue_temp_credentials(self, user_dir: str) -> dict[str, str]:
        """
        调用 STS GetFederationToken 换取限定 user_dir 的临时密钥（内存缓存复用）
        :return: {secret_id, secret_key, token}（均为临时凭证）
        :raises BusinessError: STS 调用失败或响应异常（文案面向用户，转 400）
        """
        cached = self._cred_cache.get(user_dir)
        if cached and time.time() < cached[1] - self.CRED_REFRESH_MARGIN:
            return cached[0]
        self._require_config()

        host = "sts.tencentcloudapi.com"
        service = "sts"
        version = "2018-08-13"
        now = int(time.time())
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        body = json.dumps(
            {
                "Name": "baiCosSync",
                "Policy": self._build_policy(user_dir),
                "DurationSeconds": settings.COS_CRED_SECONDS,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        # TC3 规范请求（POST JSON：content-type + host 两头参与签名）
        canonical_request = "\n".join(
            [
                "POST",
                "/",
                "",
                f"content-type:application/json\nhost:{host}\n",
                "content-type;host",
                self._sha256_hex(body),
            ]
        )
        string_to_sign = "\n".join(
            [
                "TC3-HMAC-SHA256",
                str(now),
                f"{date}/{service}/tc3_request",
                self._sha256_hex(canonical_request.encode("utf-8")),
            ]
        )
        k_date = hmac.new(
            ("TC3" + settings.COS_SECRET_KEY).encode("utf-8"), date.encode("utf-8"), hashlib.sha256
        ).digest()
        k_signing = hmac.new(
            hmac.new(k_date, service.encode("utf-8"), hashlib.sha256).digest(),
            b"tc3_request",
            hashlib.sha256,
        ).digest()
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-TC-Action": "GetFederationToken",
            "X-TC-Version": version,
            "X-TC-Timestamp": str(now),
            "X-TC-Region": settings.COS_REGION,
            "Authorization": (
                f"TC3-HMAC-SHA256 Credential={settings.COS_SECRET_ID}/{date}/{service}/tc3_request, "
                f"SignedHeaders=content-type;host, Signature={signature}"
            ),
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://{host}/", content=body, headers=headers, timeout=self.HTTP_TIMEOUT
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"STS 临时凭证换取失败（user_dir={user_dir}）：{e}")
            raise BusinessError("云存储凭证服务暂不可用，请稍后重试")

        resp_body = data.get("Response") or {}
        err = resp_body.get("Error")
        if err:
            logger.warning(
                f"STS 返回错误（user_dir={user_dir}）：{err.get('Code')} {err.get('Message')}"
            )
            raise BusinessError("云存储凭证服务暂不可用，请稍后重试")
        cred = resp_body.get("Credentials") or {}
        expired = int(resp_body.get("ExpiredTime") or 0)
        creds = {
            "secret_id": str(cred.get("TmpSecretId") or ""),
            "secret_key": str(cred.get("TmpSecretKey") or ""),
            "token": str(cred.get("Token") or ""),
        }
        if not creds["secret_id"] or not creds["secret_key"] or expired <= 0:
            raise BusinessError("云存储凭证服务响应异常，请稍后重试")
        self._cred_cache[user_dir] = (creds, expired)
        return creds

    # ==================== COS 预签名（sha1 两层 HMAC，头不参与签名） ====================

    @staticmethod
    def _cos_quote(value: str) -> str:
        """COS UrlEncode：除字母数字与 _ . - ~ 外全部编码（含 * 空格 等）"""
        return quote(value, safe="")

    def _cos_host(self) -> str:
        """
        请求主机名：优先自定义源站域名（COS_CUSTOM_DOMAIN，须已在 COS 控制台绑定桶），
        未配置回退桶默认域名。COS 签名不含 Host 头，预签名 URL 换域名不影响校验
        """
        if settings.COS_CUSTOM_DOMAIN:
            return settings.COS_CUSTOM_DOMAIN
        return f"{settings.COS_BUCKET}.cos.{settings.COS_REGION}.myqcloud.com"

    def _cos_presign_url(
        self,
        method: str,
        raw_path: str,
        creds: dict[str, str],
        params: dict[str, str] | None = None,
        ttl: int = PRESIGN_TTL,
    ) -> str:
        """
        生成 COS 预签名 URL（临时密钥签名；x-cos-security-token 追加查询串不参与签名）
        :param method: HTTP 方法（put/get，规范串小写）
        :param raw_path: 未编码的请求路径（参与签名——服务端按解码后路径构建规范串；
                 对象操作形如 /<用户 id>/<书名>.<ext>，桶清单为 /）
        :param params: 参与签名的业务查询参数（字典序规范化）
        """
        now = int(time.time())
        key_time = f"{now};{now + ttl}"
        sign_key = hmac.new(
            creds["secret_key"].encode("utf-8"), key_time.encode("utf-8"), hashlib.sha1
        ).hexdigest()
        pairs = sorted(
            (self._cos_quote(k.lower()), self._cos_quote(v)) for k, v in (params or {}).items()
        )
        param_list = ";".join(k for k, _ in pairs)
        http_params = "&".join(f"{k}={v}" for k, v in pairs)
        # HttpString 四段均以 \n 结尾：method / path / params / headers（头不参与签名为空段）
        http_string = f"{method.lower()}\n{raw_path}\n{http_params}\n\n"
        string_to_sign = (
            f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"
        )
        signature = hmac.new(
            sign_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1
        ).hexdigest()
        query = [f"{k}={v}" for k, v in pairs]
        query += [
            "q-sign-algorithm=sha1",
            f"q-ak={self._cos_quote(creds['secret_id'])}",
            f"q-sign-time={self._cos_quote(key_time)}",
            f"q-key-time={self._cos_quote(key_time)}",
            "q-header-list=",
            f"q-url-param-list={param_list}",
            f"q-signature={signature}",
        ]
        if creds.get("token"):
            # 临时密钥签名必须追加安全令牌（官方约定：查询串携带、不参与签名）
            query.append(f"x-cos-security-token={self._cos_quote(creds['token'])}")
        url_path = quote(raw_path, safe="/")
        return f"https://{self._cos_host()}{url_path}?" + "&".join(query)

    async def create_presigned_put(self, user_dir: str, title: str, ext: str) -> tuple[str, str]:
        """
        签发单本上传预签名 URL（PUT 对象；仅限该用户目录内）
        :return: (object_key, url)
        """
        creds = await self.issue_temp_credentials(user_dir)
        key = self.object_key(user_dir, title, ext)
        url = self._cos_presign_url("PUT", f"/{key}", creds)
        return key, url

    async def resolve_object_key(self, user_dir: str, title: str, ext: str) -> str | None:
        """
        按书名定位用户目录内真实对象 key（扩展名大小写不敏感）
        桶内对象扩展名大小写不保证与业务一致（如手动上传的 .TXT），下载/删除前须定位真实 key
        :return: 真实完整 key；未找到返回 None
        :raises BusinessError: 列举失败（转 400 业务错误）
        """
        clean_title = self.sanitize_segment(title)
        if not clean_title:
            return None
        prefix = f"{user_dir}/{clean_title}."
        status, content = await self._server_cos_request(
            "GET", "/", {"prefix": prefix, "max-keys": "100"}
        )
        if status != 200:
            logger.warning(f"COS 对象定位列举失败（user_dir={user_dir}）：HTTP {status}")
            raise BusinessError("云端清单查询失败，请稍后重试")
        want = ext.lower()
        root = ElementTree.fromstring(content)
        fallback: str | None = None
        for node in root.findall("Contents"):
            key = node.findtext("Key") or ""
            name = key.rsplit("/", 1)[-1]
            dot = name.rfind(".")
            if dot <= 0:
                continue
            if name[dot + 1 :].lower() != want:
                continue
            # 扩展名精确小写优先（上传恒小写，保证下载到最新上传内容）；其余大小写变体兜底
            if name[dot + 1 :] == ext.lower():
                return key
            if fallback is None:
                fallback = key
        return fallback

    async def create_presigned_get(self, user_dir: str, title: str, ext: str) -> tuple[str, str]:
        """
        签发单本下载预签名 URL（GET 对象；仅限该用户目录内；扩展名大小写不敏感定位真实 key）
        :return: (object_key, url)（未找到对象时按规范小写 key 签发，GET 404 由前端缺失哨兵处理）
        """
        key = await self.resolve_object_key(user_dir, title, ext)
        if key is None:
            key = self.object_key(user_dir, title, ext)
        creds = await self.issue_temp_credentials(user_dir)
        url = self._cos_presign_url("GET", f"/{key}", creds)
        return key, url

    # ==================== 服务端 COS 直调（永久密钥：桶列举 / 对象删除） ====================

    def _permanent_creds(self) -> dict[str, str]:
        self._require_config()
        return {
            "secret_id": settings.COS_SECRET_ID,
            "secret_key": settings.COS_SECRET_KEY,
            "token": "",
        }

    async def _server_cos_request(
        self, method: str, raw_path: str, params: dict[str, str] | None = None
    ) -> tuple[int, bytes]:
        """服务端持永久密钥直调 COS（桶列举/对象删除等管理动作；返回 HTTP 状态码与响应体）"""
        url = self._cos_presign_url(method, raw_path, self._permanent_creds(), params)
        try:
            async with httpx.AsyncClient() as client:
                if method == "DELETE":
                    resp = await client.delete(url, timeout=self.HTTP_TIMEOUT)
                else:
                    resp = await client.get(url, timeout=self.HTTP_TIMEOUT)
        except Exception as e:
            logger.warning(f"COS 服务端直调失败（{method} {raw_path}）：{e}")
            raise BusinessError("云端同步服务暂不可用，请稍后重试")
        return resp.status_code, resp.content

    # ==================== 云端书籍清单（桶列举直查） ====================

    async def list_objects(self, user_dir: str) -> list[dict]:
        """
        查询用户目录下的对象（服务端持永久密钥直查后只回传该目录结果，
        前端拿不到跨目录列举能力）
        :return: [{key, title, format, size, last_modified}]（COS 清单字典序）
        :raises BusinessError: 查询失败（转 400 业务错误）
        """
        prefix = f"{user_dir}/"
        status, content = await self._server_cos_request(
            "GET", "/", {"prefix": prefix, "max-keys": str(self.LIST_MAX_KEYS)}
        )
        if status != 200:
            logger.warning(f"COS 目录清单查询失败（user_dir={user_dir}）：HTTP {status}")
            raise BusinessError("云端清单查询失败，请稍后重试")

        # COS GetBucket 响应 XML 无命名空间（实测），直接按裸标签解析
        root = ElementTree.fromstring(content)
        items: list[dict] = []
        for node in root.findall("Contents"):
            key = node.findtext("Key") or ""
            if not key.startswith(prefix) or key == prefix:
                continue  # 跳过目录占位对象
            name = key[len(prefix) :]
            if "/" in name or name.startswith("."):
                continue  # 跳过子前缀与隐藏对象（历史 .books-index.json 残留）
            dot = name.rfind(".")
            if dot <= 0:
                continue  # 无扩展名，非书籍对象
            fmt = name[dot + 1 :].upper()
            if fmt not in ("TXT", "PDF"):
                continue  # 仅收录书籍对象
            items.append(
                {
                    "key": key,
                    "title": name[:dot],
                    "format": fmt,
                    "size": int(node.findtext("Size") or "0"),
                    "last_modified": (node.findtext("LastModified") or "").strip(),
                }
            )
        return items

    async def delete_cloud_book(self, user_dir: str, title: str, ext: str) -> None:
        """
        删除云端书籍对象（幂等：对象不存在 COS 亦返回 204；扩展名大小写不敏感定位真实 key）
        :raises BusinessError: 删除请求失败（转 400 业务错误）
        """
        clean_title = self.sanitize_segment(title)
        if not clean_title:
            raise BusinessError("书名不能为空")
        key = await self.resolve_object_key(user_dir, clean_title, ext)
        if key is None:
            return
        status, _ = await self._server_cos_request("DELETE", f"/{key}")
        if status not in (200, 204):
            logger.warning(f"云端对象删除失败（user_dir={user_dir} key={key}）：HTTP {status}")
            raise BusinessError("云端对象删除失败，请稍后重试")


# 模块级单例（全项目经 cos_service 使用）
cos_service = CosService()
