"""
用户阅读偏好路由（/api/v1/preferences）
--------------------------------------------------------------------------
- 单行 JSON 整包读写：键值集由前端定义（阅读设置 + 书架卡片样式），后端不感知内部结构
- 读取从未保存过时 prefs 为 null（前端走本地默认值）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...schemas.reading import PrefsPut
from ...services import reading_service as svc

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _ok(data: object = None) -> dict:
    """统一成功响应包装"""
    return {"code": 0, "msg": "success", "data": data}


@router.get("")
async def get_preferences(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """读取当前用户偏好配置"""
    return _ok({"prefs": await svc.get_prefs(db, user_id)})


@router.put("")
async def put_preferences(
    data: PrefsPut,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """偏好整包写入（upsert）"""
    return _ok({"prefs": await svc.put_prefs(db, user_id, data)})
