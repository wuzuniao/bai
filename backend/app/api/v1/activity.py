"""
活动奖励路由（/api/v1/activity）
--------------------------------------------------------------------------
- summary：活动页聚合数据（余额 / 今日已获 / 阅读统计 / 本周签到 / 档位状态）
- checkin：今日签到（按星期定档发放铜币）
- reading-claim：领取阅读档位奖励（当日已读达标且未领过）
- makeup：会员补签（黑铁及以上每月 3 次，实时查 auth 判定会员）
- 业务规则错误由服务层抛 ValueError，此处统一转 400
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_payload, get_current_user_id
from ...schemas.reward import MakeupRequest, ReadingClaimRequest
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


@router.post("/makeup")
async def makeup_checkin(
    data: MakeupRequest,
    payload: dict = Depends(get_current_payload),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """会员补签（按令牌 roles 声明本地判定；黑铁及以上每月 3 次，非会员/超限/日期非法返回 400）"""
    user_id = int(payload["sub"])
    roles_raw = payload.get("roles") or []
    roles = [str(r) for r in roles_raw]
    try:
        makeup_date = date.fromisoformat(data.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式不正确")
    try:
        return _ok(await svc.makeup_checkin(db, user_id, makeup_date, roles))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
