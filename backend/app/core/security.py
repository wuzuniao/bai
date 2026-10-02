"""
安全验证模块
--------------------------------------------------------------------------
用户模块独立为 auth 服务后：
- 密码/用户名/验证码校验与 JWT 签发已随用户模块迁移至 auth 服务；
- 本模块仅提供 verify_access_token：对 auth 签发的 RS256 access_token 做本地验签
  （JWKS 公钥经 auth_client 缓存；issuer=AUTH_ISSUER；零逐请求网络调用）。
"""
from __future__ import annotations

from typing import Any

import jwt

from . import auth_client
from .config import settings

# JWT 签名算法（auth 服务签发，本服务仅持公钥本地验签）
_JWT_ALGORITHM = "RS256"

# 令牌校验时间容差（秒）：容忍本服务与 auth 服务间的轻微时钟偏差
_JWT_LEEWAY_SECONDS = 60


async def verify_access_token(token: str) -> dict[str, Any]:
    """
    校验 auth 服务签发的 access_token（纯本地验签，不逐请求调用 auth）
    - 公钥来源：auth_client 的 JWKS 缓存（内存 + 磁盘），未知 kid 自动重拉
    - 校验项：RS256 签名 / iss（=AUTH_ISSUER）/ exp（leeway 60s）/ sub 存在
    :param token: JWT 字符串（前端经 Authorization: Bearer 携带）
    :return: 解码后的 payload（含 iss/sub/role/azp/jti/iat/exp）
    :raises ValueError: token 无效、已过期、签名错误或签发方不匹配
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError("令牌不能为空")
    # 1. 解析 header 获取 kid（此步不验签）
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise ValueError("登录凭证无效")
    kid = header.get("kid")

    # 2. 按 kid 取公钥（未知 kid 重拉一次 JWKS，支持 auth 密钥轮换）
    key = auth_client.get_public_key(kid)
    if key is None:
        await auth_client.fetch_jwks()
        key = auth_client.get_public_key(kid)
    if key is None:
        raise ValueError("登录凭证无效")

    # 3. 验签 + issuer + 过期校验
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[_JWT_ALGORITHM],
            issuer=settings.AUTH_ISSUER,
            leeway=_JWT_LEEWAY_SECONDS,
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("登录已过期，请重新登录")
    except jwt.InvalidIssuerError:
        raise ValueError("登录凭证签发方不正确")
    except jwt.InvalidTokenError:
        raise ValueError("登录凭证无效")

    # 4. sub 声明校验
    if "sub" not in payload:
        raise ValueError("登录凭证格式不正确")
    return payload
