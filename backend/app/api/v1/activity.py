"""
活动奖励路由（/api/v1/activity）
--------------------------------------------------------------------------
- summary：活动页聚合数据（余额 / 今日已获 / 阅读统计 / 本周签到 / 档位状态）
- checkin：今日签到（按星期定档发放铜币）
- reading-claim：领取阅读档位奖励（当日已读达标且未领过）
- 业务规则错误由服务层抛 ValueError，此处统一转 400
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...schemas.reward import ReadingClaimRequest
from ...services import reward_service as svc

router = APIRouter(prefix="/activity", tags=["activity"])


def _ok(data: object = None) -> dict:
    """统一成功响应包装"""
    return {"code": 0, "msg": "success", "data": data}


@router.get("/summary")
async def get_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """活动页聚合数据（一次拉全：余额、今日已获、阅读统计、签到、档位状态）"""
    return _ok(await svc.get_summary(db, user_id))


@router.post("/checkin")
async def checkin(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """今日签到（重复签到返回 400）"""
    try:
        return _ok(await svc.checkin(db, user_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reading-claim")
async def claim_reading_reward(
    data: ReadingClaimRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """领取阅读档位奖励（未达标/已领取返回 400）"""
    try:
        return _ok(await svc.claim_reading_reward(db, user_id, data.tier_minutes))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
