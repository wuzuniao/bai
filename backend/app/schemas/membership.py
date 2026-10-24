"""会员购买 Pydantic 校验模型（校验逻辑集中本层，路由不散写）"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MembershipPurchaseRequest(BaseModel):
    """金币购买黑铁会员（POST /membership/purchase）"""

    months: int = Field(gt=0, le=12, description="购买月数（1~12）")
