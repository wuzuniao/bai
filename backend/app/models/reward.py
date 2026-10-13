"""
活动奖励 ORM 模型（货币账户 / 货币流水 / 每日签到 / 阅读档位领取）
--------------------------------------------------------------------------
- 表结构真源见 backend/sql/create_bai_db.sql（增量见 add_activity_coins.sql）
- 外键不设物理约束（项目规范）；金币=100 银、银=100 铜（发放时服务端自动进位）
- 领取记录按 (user, date, tier) 唯一：余额被兑换/消费不影响当日领取状态、不重复发放
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BIGINT, DATE, VARCHAR, DateTime, UniqueConstraint
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class CoinAccount(Base):
    """货币账户（一人一行；铜/银满 100 自动进位后余额恒 0-99）"""

    __tablename__ = "coin_accounts"
    __table_args__ = (UniqueConstraint("user_id", name="uk_ca_user"),)

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False, comment="业务用户 id（JWT sub）")
    copper: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="铜币余额（进位后恒 0-99）")
    silver: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="银币余额（进位后恒 0-99）")
    gold: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="金币余额")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class CoinTransaction(Base):
    """货币流水（全部金银铜变动明细；今日已获铜币=当日 checkin/reading 铜币入账汇总）"""

    __tablename__ = "coin_transactions"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    coin_type: Mapped[int] = mapped_column(
        TINYINT(1), nullable=False, comment="币种 0=铜 1=银 2=金"
    )
    amount: Mapped[int] = mapped_column(nullable=False, comment="变动量（正=入账 负=扣减）")
    source: Mapped[str] = mapped_column(
        VARCHAR(32), nullable=False, comment="来源 checkin/reading/exchange/consume"
    )
    source_id: Mapped[str] = mapped_column(
        VARCHAR(64), nullable=False, default="", server_default="", comment="来源单据 id（签到/领取记录 id）"
    )
    remark: Mapped[str] = mapped_column(
        VARCHAR(100), nullable=False, default="", server_default="", comment="变动说明"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")


class CheckinRecord(Base):
    """每日签到记录（一人一日一行；连续天数由本周记录推导，不落冗余字段）

    会员补签行 is_makeup=1、reward=0（不发奖励，仅恢复签到状态）。
    """

    __tablename__ = "checkin_records"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uk_cr_user_date"),)

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    checkin_date: Mapped[date] = mapped_column(DATE, nullable=False, comment="签到日期（东八区）")
    reward: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="发放铜币数（按星期定档）")
    is_makeup: Mapped[int] = mapped_column(
        TINYINT(1), nullable=False, default=0, server_default="0",
        comment="是否补签 0=正常签到 1=会员补签（不发奖励，仅恢复签到状态）",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class ReadingRewardClaim(Base):
    """阅读时长档位奖励领取记录（达成后手动领取；按日按档唯一防重复发放）"""

    __tablename__ = "reading_reward_claims"
    __table_args__ = (
        UniqueConstraint("user_id", "claim_date", "tier_minutes", name="uk_rrc_user_date_tier"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    claim_date: Mapped[date] = mapped_column(DATE, nullable=False, comment="达成统计日期（东八区）")
    tier_minutes: Mapped[int] = mapped_column(nullable=False, comment="档位阈值分钟数（5/30/120/360/720）")
    reward: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="发放铜币数（基础+额外赠送）")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )
