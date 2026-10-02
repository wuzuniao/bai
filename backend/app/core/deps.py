"""
FastAPI 依赖：认证依赖
--------------------------------------------------------------------------
提供 `get_current_payload` 与 `get_current_user_id` 依赖函数，受保护接口通过
`Depends(get_current_user_id)` 获取当前登录用户ID，或经
`Depends(get_current_payload)` 获取完整令牌 claims（含 roles/azp）。

安全校验：
1. RS256 签名 + issuer + 过期校验（security.verify_access_token，本地公钥验签）
2. 令牌撤销本地比对（auth_client.is_revoked：iat < 该用户最新撤销时刻 → 401）

用法：
    from fastapi import Depends
    from .core.deps import get_current_user_id

    @router.get("/me")
    async def me(user_id: int = Depends(get_current_user_id)):
        ...
"""
from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException

from . import auth_client
from .security import verify_access_token


async def _authenticate_and_validate(authorization: str | None) -> dict[str, Any]:
    """
    解析 access_token 并完成本地校验
    :param authorization: 请求头 Authorization 字段
    :return: 令牌 payload（含 iss/sub/roles/azp/jti/iat/exp）
    :raises HTTPException: 401 未登录/无效/过期/已撤销
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    # 校验 Bearer 前缀（RFC 6750）
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="认证凭证格式不正确")
    token = parts[1].strip()
    try:
        payload = await verify_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="登录凭证格式不正确")
    if user_id <= 0:
        raise HTTPException(status_code=401, detail="登录凭证无效")

    # 令牌撤销本地比对（数据源为后台增量同步，每请求零网络调用）
    if auth_client.is_revoked(user_id, payload.get("iat", 0)):
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    return payload


async def get_current_payload(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    从请求头 Authorization 解析 access_token，本地验签后返回完整令牌 claims
    :param authorization: 请求头 Authorization 字段，格式 "Bearer <access_token>"
    :return: payload（含 iss/sub/roles/azp/jti/iat/exp）
    :raises HTTPException: 401 未携带 token / token 无效 / token 已过期 / token 已撤销
    """
    return await _authenticate_and_validate(authorization)


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> int:
    """
    从请求头 Authorization 解析 access_token，本地验签后返回当前登录用户ID
    :param authorization: 请求头 Authorization 字段，格式 "Bearer <access_token>"
    :return: 当前用户ID
    :raises HTTPException: 401 未携带 token / token 无效 / token 已过期 / token 已撤销
    """
    payload = await _authenticate_and_validate(authorization)
    return int(payload["sub"])
