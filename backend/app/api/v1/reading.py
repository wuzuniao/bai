"""
阅读行为路由（/api/v1/reading）
--------------------------------------------------------------------------
- 阅读时长：前端按次结算上报（onHide/onUnload），服务端按东八区按日累加
- 统计：书架统计卡与福利页的今日/累计分钟数
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...schemas.reading import MinutesReport
from ...services import reading_service as svc

router = APIRouter(prefix="/reading", tags=["reading"])


def _ok(data: object = None) -> dict:
    """统一成功响应包装"""
    return {"code": 0, "msg": "success", "data": data}


@router.post("/minutes")
async def report_minutes(
    data: MinutesReport,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """单次阅读结算上报（分钟数累加至今日），返回今日与累计分钟数"""
    return _ok(await svc.add_minutes(db, user_id, data.minutes))


@router.get("/stats")
async def get_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """今日与累计阅读分钟数"""
    return _ok(await svc.get_stats(db, user_id))
