"""
会员购买路由（/api/v1/membership）
--------------------------------------------------------------------------
- purchase：金币购买黑铁会员（微信小程序金币支付通道；按月购买 1~12 个月）
- 计价服务端真源（1 金币/月、单月按 31 天计），前端仅传月数不可传价格；APP 端
  应用商店内购不经此端点
- 业务规则错误由服务层抛 ValueError，此处统一转 400
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...schemas.membership import MembershipPurchaseRequest
from ...services import membership_service as svc

router = APIRouter(prefix="/membership", tags=["membership"])


def _ok(data: object = None) -> dict:
    """统一成功响应包装"""
    return {"code": 0, "msg": "success", "data": data}


@router.post("/purchase")
async def purchase(
    data: MembershipPurchaseRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """金币购买黑铁会员（余额不足 / 授权失败退款后返回 400）"""
    try:
        return _ok(await svc.purchase_membership(db, user_id, data.months))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
