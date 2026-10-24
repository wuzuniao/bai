"""
会员购买服务（微信小程序金币支付通道，面向对象：MembershipService 类）
--------------------------------------------------------------------------
- 商品计价服务端真源：价格/时长/角色不可由前端传入（防篡改）；APP 端
  应用商店内购不经此流程
- 编排：本地事务扣金币（FOR UPDATE + 流水，提交即生效）→ 服务间调 auth
  授权会员角色（order_no 幂等，续费顺延）→ 授权失败补偿退款金币
- 跨系统一致性：先扣币后授权，授权失败即时退款；退款失败的极端场景
  记录错误日志人工处理（金币已扣、会员未开通）
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth_client import auth_client  # 模块级单例实例（勿导入模块本身）
from ..core.exceptions import BusinessError
from ..utils.logger import logger
from .reward_service import reward_service  # 模块级单例实例（勿导入模块本身）


class MembershipService:
    """会员购买服务（金币支付 → auth 授权 → 失败补偿退款）"""

    # 会员商品（黑铁会员月卡；与 member-pay 页金币版文案一致，按月购买）
    MEMBERSHIP_ROLE_CODE = "iron"
    MONTH_DURATION_DAYS = 31  # 单月时长（天，按 31 天计）
    MONTH_PRICE_GOLD = 1  # 单月价格（金币）
    MEMBERSHIP_CURRENCY = "gold"

    async def purchase_membership(
        self, db: AsyncSession, user_id: int, months: int
    ) -> dict[str, Any]:
        """
        金币购买黑铁会员：扣 months 金币 → 调 auth 授 iron 角色 months*30 天
        失败路径：金币不足 400；授权失败自动退款后 400（金币退回）
        :return: {order_no, months, amount_gold, role_code, expires_at, balance}
        """
        duration_days = months * self.MONTH_DURATION_DAYS
        price_gold = months * self.MONTH_PRICE_GOLD
        order_no = f"bai-{uuid.uuid4().hex}"

        # 1. 本地扣金币（先落账；授权为远程调用，失败走补偿退款）
        balance = await reward_service.debit_gold(
            db, user_id, price_gold, order_no, f"黑铁会员月卡购买 ×{months}"
        )
        await db.commit()

        # 2. 服务间授权（order_no 幂等；auth 侧续费顺延 + 扇出令牌撤销）
        try:
            grant = await auth_client.grant_membership(
                user_id=user_id,
                role_code=self.MEMBERSHIP_ROLE_CODE,
                duration_days=duration_days,
                order_no=order_no,
                amount=float(price_gold),
                currency=self.MEMBERSHIP_CURRENCY,
            )
        except Exception as e:
            logger.error(f"会员授权失败（order_no={order_no}）：{e}")
            # 3. 补偿退款（独立提交；退款失败属极端场景，记日志人工处理）
            try:
                await reward_service.refund_gold(
                    db, user_id, price_gold, order_no, "会员购买失败退款"
                )
            except Exception:
                logger.exception(
                    f"会员购买退款补偿失败，须人工处理 order_no={order_no} user_id={user_id}"
                )
            raise BusinessError("会员开通失败，金币已退回，请稍后重试")

        return {
            "order_no": order_no,
            "months": months,
            "amount_gold": price_gold,
            "role_code": grant.get("role_code", self.MEMBERSHIP_ROLE_CODE),
            "expires_at": grant.get("expires_at", ""),
            "balance": balance,
        }


# 模块级单例
membership_service = MembershipService()
