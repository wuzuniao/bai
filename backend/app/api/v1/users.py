"""
用户模块路由（/api/v1/users）
--------------------------------------------------------------------------
说明：注册/登录/资料管理等用户接口由 auth 统一认证服务提供（前端直连，
不经本后端转发）。本模块仅提供登录态验证端点：业务前端/联调可用其确认
「auth 签发的令牌在本服务可正常本地验签」，后续业务接口经
Depends(get_current_user_id) 获取当前用户。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.deps import get_current_payload

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(payload: dict = Depends(get_current_payload)) -> dict:
    """
    当前登录用户（本地验签通过即返回令牌主体信息）
    - 用于开发联调与后续业务接口的用户身份入口
    """
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "id": int(payload["sub"]),
            "role": payload.get("role"),
            "azp": payload.get("azp"),
        },
    }
