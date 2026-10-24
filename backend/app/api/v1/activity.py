"""
活动奖励路由（/api/v1/activity）
--------------------------------------------------------------------------
- summary：活动页聚合数据（余额 / 今日已获 / 阅读统计 / 本周签到 / 档位状态）
- checkin：今日签到（按星期定档发放铜币）
- reading-claim：领取阅读档位奖励（当日已读达标且未领过）
- makeup：会员补签（黑铁及以上每月 3 次，按令牌 roles 声明本地判定）
- 业务规则错误由服务层抛 BusinessError，此处统一转 400
- 响应统一经 core/response.py 的 response_service 包装 {code, msg, data}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_payload, get_current_user_id
from ...core.exceptions import BusinessError
from ...core.response import response_service
from ...schemas.reward import MakeupRequest, ReadingClaimRequest
from ...services.reward_service import reward_service as svc

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/summary")
async def get_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """活动页聚合数据（一次拉全：余额、今日已获、阅读统计、签到、档位状态）"""
    return response_service.ok(await svc.get_summary(db, user_id))


@router.post("/checkin")
async def checkin(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """今日签到（重复签到返回 400）"""
    try:
        return response_service.ok(await svc.checkin(db, user_id))
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reading-claim")
async def claim_reading_reward(
    data: ReadingClaimRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """领取阅读档位奖励（未达标/已领取返回 400）"""
    try:
        return response_service.ok(await svc.claim_reading_reward(db, user_id, data.tier_minutes))
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/makeup")
async def makeup_checkin(
    data: MakeupRequest,
    payload: dict = Depends(get_current_payload),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """会员补签（按令牌 roles 声明本地判定；黑铁及以上每月 3 次，非会员/超限/日期非法返回 400）"""
    user_id = int(payload["sub"])
    roles = [str(r) for r in (payload.get("roles") or [])]
    try:
        return response_service.ok(await svc.makeup_checkin(db, user_id, data.date, roles))
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))
