"""
活动奖励服务层（货币账户 / 签到 / 阅读时长档位奖励，面向对象：RewardService 类）
--------------------------------------------------------------------------
- 业务规则（与 backend/sql/add_activity_coins.sql 头注一致）：
  - 签到：自然周口径，周一~周五 +5 铜币、周六 +10、周日大礼 +20；
    「已连续签到」= 本周从周一起的连续签到天数（断签从缺口次日重计，
    新的一周自然重计，与「断签或领奖后重新计算」文案一致）
  - 阅读档位：按日独立领取，5'/30'/120'/360'/720' 五档，档内奖励=基础+额外赠送；
    时长上报确认后自动发放已达成的未领取档位（auto_claim_reached），无需手动领取；
    领取记录按 (user, date, tier) 唯一——余额被兑换/消费扣除后不影响
    当日领取状态，不会随阅读时长重复发放
  - 自动兑换：铜满 100 进 1 银、银满 100 进 1 金，入账时服务端自动进位，
    产生成对增减流水
- 发放入账（_credit）不 commit，由签到/领取入口统一提交，保证记录、
  余额、流水同事务原子生效
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CheckinRecord, CoinAccount, CoinTransaction, ReadingRewardClaim, ReadingDailyStat
from ..utils.timezone import TimezoneUtil
from .reading_service import reading_service

# 每日签到基准奖励（索引 0=周一 ... 6=周日满勤大礼；周末两天的实际发放额按本周漏签天数顺延递减）
CHECKIN_REWARDS: list[int] = [5, 5, 5, 5, 5, 10, 20]

# 周末奖励按本周（周一~昨日）漏签天数顺延递减：周六漏 0 天 +10、漏 ≥1 天 +5；
# 周日漏 0 天 +20、漏 1 天 +10、漏 ≥2 天 +5 保底（键=weekday，5=周六 6=周日）
WEEKEND_REWARDS_BY_MISS: dict[int, list[int]] = {5: [10, 5], 6: [20, 10, 5]}

# 阅读档位（阈值分钟, 基础奖励, 额外赠送）
READING_TIERS: list[tuple[int, int, int]] = [
    (5, 1, 0),
    (30, 6, 0),
    (120, 24, 10),
    (360, 72, 30),
    (720, 144, 60),
]

# 币种编码
COIN_COPPER = 0
COIN_SILVER = 1
COIN_GOLD = 2

# 流水来源
SOURCE_CHECKIN = "checkin"
SOURCE_READING = "reading"
SOURCE_EXCHANGE = "exchange"
SOURCE_CONSUME = "consume"

# 自动兑换比率
COPPER_PER_SILVER = 100
SILVER_PER_GOLD = 100

# 档位状态（接口取值）
STATE_LOCKED = "locked"
STATE_CLAIMABLE = "claimable"
STATE_CLAIMED = "claimed"


class RewardService:
    """活动奖励服务（余额 / 签到 / 补签 / 阅读档位奖励 / 金币支出与退款）"""

    @staticmethod
    def balance_to_dict(account: CoinAccount | None) -> dict[str, int]:
        """账户行 → 余额字典（无账户行时全 0）"""
        if account is None:
            return {"gold": 0, "silver": 0, "copper": 0}
        return {"gold": account.gold, "silver": account.silver, "copper": account.copper}


    async def _today_gained_copper(self, db: AsyncSession, user_id: int, today: date) -> int:
        """今日已获铜币 = 当日签到+阅读的铜币入账汇总（兑换增减不计入）"""
        result = await db.execute(
            select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                CoinTransaction.user_id == user_id,
                CoinTransaction.coin_type == COIN_COPPER,
                CoinTransaction.amount > 0,
                CoinTransaction.source.in_((SOURCE_CHECKIN, SOURCE_READING)),
                func.date(CoinTransaction.created_at) == today,
            )
        )
        return int(result.scalar_one() or 0)


    async def _credit(self, 
        db: AsyncSession,
        user_id: int,
        amount: int,
        source: str,
        source_id: str,
        remark: str,
    ) -> None:
        """
        铜币入账 + 自动进位兑换 + 流水（不 commit，由调用方统一提交保证原子性）
        - FOR UPDATE 锁账户行防并发丢失更新；首笔发放时建户
        - 满额进位产生成对增减流水（铜 -100 / 银 +1；银 -100 / 金 +1）
        """
        result = await db.execute(
            select(CoinAccount).where(CoinAccount.user_id == user_id).with_for_update()
        )
        account = result.scalar_one_or_none()
        if account is None:
            account = CoinAccount(user_id=user_id)
            db.add(account)
            await db.flush()

        def _flow(coin_type: int, flow_amount: int, flow_remark: str, flow_source: str, flow_source_id: str) -> None:
            db.add(
                CoinTransaction(
                    user_id=user_id,
                    coin_type=coin_type,
                    amount=flow_amount,
                    source=flow_source,
                    source_id=flow_source_id,
                    remark=flow_remark,
                )
            )

        account.copper += amount
        _flow(COIN_COPPER, amount, remark, source, source_id)
        while account.copper >= COPPER_PER_SILVER:
            account.copper -= COPPER_PER_SILVER
            account.silver += 1
            _flow(COIN_COPPER, -COPPER_PER_SILVER, "100 铜币自动兑换 1 银币", SOURCE_EXCHANGE, "")
            _flow(COIN_SILVER, 1, "100 铜币自动兑换 1 银币", SOURCE_EXCHANGE, "")
        while account.silver >= SILVER_PER_GOLD:
            account.silver -= SILVER_PER_GOLD
            account.gold += 1
            _flow(COIN_SILVER, -SILVER_PER_GOLD, "100 银币自动兑换 1 金币", SOURCE_EXCHANGE, "")
            _flow(COIN_GOLD, 1, "100 银币自动兑换 1 金币", SOURCE_EXCHANGE, "")


    def _week_monday(self, today: date) -> date:
        """本周周一日期（自然周口径）"""
        return today - timedelta(days=today.weekday())


    async def debit_gold(self, 
        db: AsyncSession,
        user_id: int,
        amount: int,
        source_id: str,
        remark: str,
    ) -> dict[str, int]:
        """
        金币支出（不 commit，由调用方统一提交保证原子性）
        - FOR UPDATE 锁账户行防并发超扣；无账户行或余额不足抛 ValueError
        - 金币为最高币种，扣减不产生进位/兑换流水，仅写一条负流水
        :return: 扣减后余额字典
        """
        if amount <= 0:
            raise ValueError("扣减数额无效")
        result = await db.execute(
            select(CoinAccount).where(CoinAccount.user_id == user_id).with_for_update()
        )
        account = result.scalar_one_or_none()
        if account is None or account.gold < amount:
            raise ValueError("金币余额不足")
        account.gold -= amount
        db.add(
            CoinTransaction(
                user_id=user_id,
                coin_type=COIN_GOLD,
                amount=-amount,
                source=SOURCE_CONSUME,
                source_id=source_id,
                remark=remark,
            )
        )
        return {"gold": account.gold, "silver": account.silver, "copper": account.copper}


    async def refund_gold(self, 
        db: AsyncSession,
        user_id: int,
        amount: int,
        source_id: str,
        remark: str,
    ) -> None:
        """金币退款补偿（购买失败回滚；独立事务即时提交）"""
        if amount <= 0:
            raise ValueError("退款数额无效")
        result = await db.execute(
            select(CoinAccount).where(CoinAccount.user_id == user_id).with_for_update()
        )
        account = result.scalar_one_or_none()
        if account is None:
            account = CoinAccount(user_id=user_id)
            db.add(account)
            await db.flush()
        account.gold += amount
        db.add(
            CoinTransaction(
                user_id=user_id,
                coin_type=COIN_GOLD,
                amount=amount,
                source=SOURCE_CONSUME,
                source_id=source_id,
                remark=remark,
            )
        )
        await db.commit()


    def _weekend_reward(self, weekday: int, missed_days: int) -> int:
        """周末签到奖励：按本周（周一~昨日）漏签天数顺延递减（周六漏 ≥1 天降至 +5；周日 0 漏 +20 / 1 漏 +10 / ≥2 漏 +5 保底）"""
        ladder = WEEKEND_REWARDS_BY_MISS[weekday]
        return ladder[min(missed_days, len(ladder) - 1)]


    def _missed_days_before(self, dates: set[date], today: date) -> int:
        """本周一~昨日中的漏签天数（今日未签不计漏——当天尚未结束）"""
        elapsed = (today - self._week_monday(today)).days
        signed_before = sum(1 for d in dates if d < today)
        return elapsed - signed_before


    def _streak_days(self, dates: set[date], today: date) -> int:
        """
        已连续签到天数：从今日往回数连续已签日期（断签停在缺口后重计，
        最多数到本周一——新的一周自然重计，与「断签或领奖后重新计算」一致）
        """
        streak = 0
        d = today
        monday = self._week_monday(today)
        while d >= monday and d in dates:
            streak += 1
            d -= timedelta(days=1)
        return streak


    # ==================== 查询 ====================


    async def get_summary(self, db: AsyncSession, user_id: int) -> dict[str, Any]:
        """活动页聚合数据：余额 / 今日已获 / 阅读统计 / 本周签到 / 今日档位状态"""
        today = TimezoneUtil.today()
        monday = self._week_monday(today)

        acc_row = await db.execute(select(CoinAccount).where(CoinAccount.user_id == user_id))
        balance = self.balance_to_dict(acc_row.scalar_one_or_none())

        # 本周签到记录（周一 ~ 今日）
        rec_rows = await db.execute(
            select(CheckinRecord.checkin_date).where(
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date.between(monday, today),
            )
        )
        checkin_dates = set(rec_rows.scalars().all())
        checked_weekdays = {d.weekday() + 1 for d in checkin_dates}

        # 今日档位领取记录
        claim_rows = await db.execute(
            select(ReadingRewardClaim.tier_minutes).where(
                ReadingRewardClaim.user_id == user_id,
                ReadingRewardClaim.claim_date == today,
            )
        )
        claimed_tiers = set(claim_rows.scalars().all())

        stats = await reading_service.get_stats(db, user_id)
        today_minutes = stats["today_minutes"]

        # 本月已补签次数（自然月，按补签操作时刻计数；前端据此展示剩余次数）
        makeup_used = int(
            await db.scalar(
                select(func.count()).select_from(CheckinRecord).where(
                    CheckinRecord.user_id == user_id,
                    CheckinRecord.is_makeup == 1,
                    CheckinRecord.created_at >= today.replace(day=1),
                )
            ) or 0
        )

        tiers: list[dict[str, Any]] = []
        for tier_minutes, base, bonus in READING_TIERS:
            if tier_minutes in claimed_tiers:
                state = STATE_CLAIMED
            elif today_minutes >= tier_minutes:
                state = STATE_CLAIMABLE
            else:
                state = STATE_LOCKED
            tiers.append(
                {
                    "tier_minutes": tier_minutes,
                    "base": base,
                    "bonus": bonus,
                    "state": state,
                }
            )

        return {
            "balance": balance,
            "today_gained": await self._today_gained_copper(db, user_id, today),
            "reading": stats,
            "checkin": {
                "streak_days": self._streak_days(checkin_dates, today),
                "checked_today": today in checkin_dates,
                "makeup_used": makeup_used,
                # 7 天格子（周一~周日）：checked 由本周签到记录推导；周六/周日按当前漏签数顺延递减
                "days": [
                    {
                        "weekday": i + 1,
                        "reward": self._weekend_reward(i, self._missed_days_before(checkin_dates, today)) if i in (5, 6) else reward,
                        "checked": (i + 1) in checked_weekdays,
                    }
                    for i, reward in enumerate(CHECKIN_REWARDS)
                ],
            },
            "reading_tiers": tiers,
        }


    # ==================== 签到 ====================


    async def checkin(self, db: AsyncSession, user_id: int) -> dict[str, Any]:
        """
        今日签到发放铜币，返回奖励、连续天数与最新余额
        - 周一~周六按基准档发放；周日按本周（周一~昨日）漏签天数顺延递减（满勤 +20 / 漏 1 +10 / 漏 ≥2 +5）
        """
        today = TimezoneUtil.today()
        exists = await db.execute(
            select(CheckinRecord.id).where(
                CheckinRecord.user_id == user_id, CheckinRecord.checkin_date == today
            )
        )
        if exists.scalar_one_or_none() is not None:
            raise ValueError("今日已签到")

        # 本周已签日期（不含今日——今日尚未签），供周日定档与签到后连续天数复用
        dates_before_rows = await db.execute(
            select(CheckinRecord.checkin_date).where(
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date.between(self._week_monday(today), today),
            )
        )
        dates_before = set(dates_before_rows.scalars().all())

        if today.weekday() in WEEKEND_REWARDS_BY_MISS:
            reward = self._weekend_reward(today.weekday(), self._missed_days_before(dates_before, today))
        else:
            reward = CHECKIN_REWARDS[today.weekday()]
        record = CheckinRecord(user_id=user_id, checkin_date=today, reward=reward)
        db.add(record)
        try:
            await db.flush()  # 取记录 id 供流水关联；唯一约束兜底并发双击
        except IntegrityError:
            await db.rollback()
            raise ValueError("今日已签到")

        await self._credit(db, user_id, reward, SOURCE_CHECKIN, str(record.id), "每日签到")
        await db.commit()

        acc_row = await db.execute(select(CoinAccount).where(CoinAccount.user_id == user_id))
        dates = set(dates_before)
        dates.add(today)
        return {
            "reward": reward,
            "streak_days": self._streak_days(dates, today),
            "checked_today": True,
            "balance": self.balance_to_dict(acc_row.scalar_one_or_none()),
            "today_gained": await self._today_gained_copper(db, user_id, today),
        }


    # ==================== 会员补签 ====================


    # 会员每月补签次数（自然月，按补签操作时刻计数；与会员页文案「每月赠 3 次」一致）
    MAKEUP_QUOTA_PER_MONTH = 3

    # 可享补签权益的角色（黑铁及以上档位 + 管理员；从令牌 roles 声明本地判定）
    MAKEUP_ROLE_CODES: list[str] = ["iron", "bronze", "silver", "gold", "admin"]


    async def makeup_checkin(self, 
        db: AsyncSession, user_id: int, makeup_date: date, roles: list[str]
    ) -> dict[str, Any]:
        """
        会员补签：恢复指定漏签日的签到状态并按当天基准档发放铜币
        （is_makeup=1；连续天数推导基于签到日期集合，自动包含补签日）
        - 会员判定按令牌 roles 声明本地比对（黑铁及以上档位/管理员），不实时查 auth
        - 被补日期须为本周一至昨日（与活动页可点格子一致）且无签到记录
        - 每自然月限 MAKEUP_QUOTA_PER_MONTH 次（按补签操作时刻所在月计数）
        :return: {makeup_date, reward, makeup_used, makeup_left, streak_days, balance, today_gained}
        """
        today = TimezoneUtil.today()
        if makeup_date >= today:
            raise ValueError("只能补签今天之前的漏签日")
        if makeup_date < self._week_monday(today):
            raise ValueError("只能补签本周内的漏签日")

        if not any(code in roles for code in self.MAKEUP_ROLE_CODES):
            raise ValueError("开通会员后每月可补签 3 次")

        exists = await db.execute(
            select(CheckinRecord.id).where(
                CheckinRecord.user_id == user_id, CheckinRecord.checkin_date == makeup_date
            )
        )
        if exists.scalar_one_or_none() is not None:
            raise ValueError("该日已签到")

        # 本月已补签次数（created_at=补签操作时刻，跨月补签日也计入操作月）
        month_start = today.replace(day=1)
        used = int(
            await db.scalar(
                select(func.count()).select_from(CheckinRecord).where(
                    CheckinRecord.user_id == user_id,
                    CheckinRecord.is_makeup == 1,
                    CheckinRecord.created_at >= month_start,
                )
            ) or 0
        )
        if used >= self.MAKEUP_QUOTA_PER_MONTH:
            raise ValueError("本月补签次数已用完")

        # 奖励按被补日期星期基准档（周一~五 +5 / 周六 +10 / 周日 +20）
        reward = CHECKIN_REWARDS[makeup_date.weekday()]
        record = CheckinRecord(user_id=user_id, checkin_date=makeup_date, reward=reward, is_makeup=1)
        db.add(record)
        try:
            await db.flush()  # 取记录 id 供流水关联；唯一约束 (user_id, checkin_date) 兜底并发重复补签
        except IntegrityError:
            await db.rollback()
            raise ValueError("该日已签到")

        await self._credit(db, user_id, reward, SOURCE_CHECKIN, str(record.id), "会员补签")
        await db.commit()

        rows = await db.execute(
            select(CheckinRecord.checkin_date).where(
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date.between(self._week_monday(today), today),
            )
        )
        dates = set(rows.scalars().all())
        acc_row = await db.execute(select(CoinAccount).where(CoinAccount.user_id == user_id))
        return {
            "makeup_date": makeup_date.isoformat(),
            "reward": reward,
            "makeup_used": used + 1,
            "makeup_left": self.MAKEUP_QUOTA_PER_MONTH - used - 1,
            "streak_days": self._streak_days(dates, today),
            "balance": self.balance_to_dict(acc_row.scalar_one_or_none()),
            "today_gained": await self._today_gained_copper(db, user_id, today),
        }


    # ==================== 阅读档位奖励 ====================


    async def claim_reading_reward(self, db: AsyncSession, user_id: int, tier_minutes: int) -> dict[str, Any]:
        """
        领取阅读档位奖励（须当日已读达标且未领过；唯一约束兜底并发重复领取）
        返回领取额、档位状态与最新余额
        """
        tier = next((t for t in READING_TIERS if t[0] == tier_minutes), None)
        if tier is None:
            raise ValueError("领取档位不存在")
        base, bonus = tier[1], tier[2]

        today = TimezoneUtil.today()
        exists = await db.execute(
            select(ReadingRewardClaim.id).where(
                ReadingRewardClaim.user_id == user_id,
                ReadingRewardClaim.claim_date == today,
                ReadingRewardClaim.tier_minutes == tier_minutes,
            )
        )
        if exists.scalar_one_or_none() is not None:
            raise ValueError("该档位奖励已领取")

        minutes_row = await db.execute(
            select(ReadingDailyStat.minutes).where(
                ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today
            )
        )
        today_minutes = int(minutes_row.scalar_one_or_none() or 0)
        if today_minutes < tier_minutes:
            raise ValueError("阅读时长未达标，还不能领取")

        reward = base + bonus
        record = ReadingRewardClaim(
            user_id=user_id, claim_date=today, tier_minutes=tier_minutes, reward=reward
        )
        db.add(record)
        try:
            await db.flush()  # 取记录 id 供流水关联；唯一约束兜底并发重复领取
        except IntegrityError:
            await db.rollback()
            raise ValueError("该档位奖励已领取")

        await self._credit(db, user_id, reward, SOURCE_READING, str(record.id), f"阅读 {tier_minutes} 分钟奖励")
        await db.commit()

        acc_row = await db.execute(select(CoinAccount).where(CoinAccount.user_id == user_id))
        return {
            "tier_minutes": tier_minutes,
            "reward": reward,
            "balance": self.balance_to_dict(acc_row.scalar_one_or_none()),
            "today_gained": await self._today_gained_copper(db, user_id, today),
        }


    async def auto_claim_reached(self, db: AsyncSession, user_id: int) -> list[dict[str, int]]:
        """
        自动领取今日已达成且未领取的全部阅读档位奖励（时长上报确认后调用，无需手动领取）
        - 先一次查齐今日分钟数与已领取档位，只对可领档位逐个发放（复用 claim_reading_reward，
          各自提交事务；并发重复领取由唯一约束兜底，业务异常静默跳过待下次发放）
        - 返回本次实际发放清单（tier_minutes + reward），供前端提示到账
        """
        today = TimezoneUtil.today()
        minutes_row = await db.execute(
            select(ReadingDailyStat.minutes).where(
                ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today
            )
        )
        today_minutes = int(minutes_row.scalar_one_or_none() or 0)
        if today_minutes <= 0:
            return []
        claimed_rows = await db.execute(
            select(ReadingRewardClaim.tier_minutes).where(
                ReadingRewardClaim.user_id == user_id, ReadingRewardClaim.claim_date == today
            )
        )
        claimed_minutes = set(claimed_rows.scalars().all())
        issued: list[dict[str, int]] = []
        for tier_minutes, _base, _bonus in READING_TIERS:
            if today_minutes < tier_minutes or tier_minutes in claimed_minutes:
                continue
            try:
                result = await self.claim_reading_reward(db, user_id, tier_minutes)
            except ValueError:
                continue  # 已领取（并发）/未达标（统计滞后）等业务异常，跳过待下次
            issued.append({"tier_minutes": tier_minutes, "reward": int(result["reward"])})
        return issued


# 模块级单例
reward_service = RewardService()
