"""
阅读行为路由（/api/v1/reading）
--------------------------------------------------------------------------
- 阅读时长：前端按次结算上报（onHide/onUnload），服务端按东八区按日累加；
  上报确认后自动发放已达成的阅读档位奖励（签到仍由用户手动点击）
- 统计：书架统计卡与福利页的今日/累计分钟数
- 响应统一经 core/response.py 的 response_service 包装 {code, msg, data}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...core.response import response_service
from ...schemas.reading import MinutesReport, ReportQuery, SessionsReport
from ...services.reading_service import reading_service as svc
from ...services.reward_service import reward_service as reward_svc
from ...utils.timezone import TimezoneUtil

router = APIRouter(prefix="/reading", tags=["reading"])


@router.post("/minutes")
async def report_minutes(
    data: MinutesReport,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """单次阅读结算上报（分钟数累加至今日）；随后自动发放已达成的阅读档位奖励"""
    stats = await svc.add_minutes(db, user_id, data.minutes)
    claimed = await reward_svc.auto_claim_reached(db, user_id)
    return response_service.ok({**stats, "claimed": claimed})


@router.post("/sessions")
async def report_sessions(
    data: SessionsReport,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """阅读会话流水批量上报（按书/时段明细账；书籍无效的条目跳过），返回落库条数"""
    return response_service.ok({"accepted": await svc.add_sessions(db, user_id, data)})


@router.get("/stats")
async def get_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """今日与累计阅读分钟数"""
    return response_service.ok(await svc.get_stats(db, user_id))


@router.get("/report")
async def get_reading_report(
    params: ReportQuery = Depends(),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """阅读统计报告（周期指标/趋势分布/阅读最久书籍/时段分布综合报表）"""
    anchor_date = params.anchor if params.anchor is not None else TimezoneUtil.today()
    try:
        report = await svc.get_report(db, user_id, params.period, anchor_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return response_service.ok(report)
