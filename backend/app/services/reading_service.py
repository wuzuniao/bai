"""
阅读业务服务层（书籍元数据 / 笔记 / 书签 / 时长 / 偏好，面向对象：ReadingService 类）
--------------------------------------------------------------------------
- 全部按 user_id 隔离查询；书籍不存在等资源缺失由调用方（路由层）判空转 404
- 业务规则错误抛 ValueError（路由层统一转 400）
- 时间统一东八区（数据库会话已 SET time_zone='+08:00'，此处写入 naive 东八区值）
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ReadingBookmark, ReadingDailyStat, ReadingNote, ReadingSession, UserBook, UserPreference
from ..schemas.reading import (
    BookCreate,
    BookmarksReplace,
    BookOrderBatch,
    BookProgressUpdate,
    PrefsPut,
    SessionsReport,
    ThoughtCreate,
    UnderlineUpsert,
)
from ..utils.timezone import TimezoneUtil

# 书籍删除时应用层级联清理的子资源（外键不设物理约束，规范约定）
NOTE_TYPE_UNDERLINE = 0
NOTE_TYPE_THOUGHT = 1

# 首页诗词《无题》虚拟书 id：内容全局固定，无 user_books 行（不进书架、无进度），
# 划线/想法以 book_id=0 落 reading_notes，按 user_id 天然隔离；坐标约定 cid=0 唯一章、
# origin=诗行序号（0-15）、字符区间含行尾标点（每行 7 字 + 标点共 8 位）
VIRTUAL_BOOK_ID = 0


class ReadingService:
    """阅读业务服务（书籍 / 划线想法 / 书签 / 时长 / 偏好 / 统计报告）"""

    @staticmethod
    def fmt_dt(dt: datetime | None) -> str | None:
        """DATETIME → 接口时间格式（YYYY-MM-DD HH:mm:ss）"""
        return None if dt is None else dt.strftime("%Y-%m-%d %H:%M:%S")


    @staticmethod
    def book_to_dict(book: UserBook) -> dict[str, Any]:
        """书籍 ORM → 接口字典（时间格式化，DECIMAL 转 float）"""
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "format": book.format,
            "size": book.size,
            "chapter_count": book.chapter_count,
            "has_preface": bool(book.has_preface),
            "sort_order": book.sort_order,
            "last_read_at": ReadingService.fmt_dt(book.last_read_at),
            "last_chapter": book.last_chapter,
            "last_page_index": book.last_page_index,
            "last_scroll_top": book.last_scroll_top,
            "last_percent": book.last_percent,
            "pdf_ratio": float(book.pdf_ratio),
            "created_at": ReadingService.fmt_dt(book.created_at),
            "updated_at": ReadingService.fmt_dt(book.updated_at),
        }


    async def get_book(self, db: AsyncSession, user_id: int, book_id: int) -> UserBook | None:
        """按 id 取当前用户的书籍（不存在/非本人返回 None）"""
        result = await db.execute(
            select(UserBook).where(UserBook.id == book_id, UserBook.user_id == user_id)
        )
        return result.scalar_one_or_none()


    async def list_books(self, db: AsyncSession, user_id: int) -> list[UserBook]:
        """书架列表（按手动排序序返回，本地缓存顺序即该顺序）"""
        result = await db.execute(
            select(UserBook)
            .where(UserBook.user_id == user_id)
            .order_by(UserBook.sort_order.asc(), UserBook.id.asc())
        )
        return list(result.scalars().all())


    async def register_book(self, db: AsyncSession, user_id: int, data: BookCreate) -> tuple[UserBook, bool]:
        """
        导入登记：同用户同名书复用已有行（跨设备按书名关联），否则新建
        :return: (书籍, 是否新建)
        """
        result = await db.execute(
            select(UserBook).where(UserBook.user_id == user_id, UserBook.title == data.title)
        )
        book = result.scalar_one_or_none()
        if book is not None:
            book.format = data.format
            book.size = data.size
            book.chapter_count = data.chapter_count
            book.has_preface = data.has_preface
            await db.commit()
            return book, False
        # 新增书置顶到书架最前（当前最小序 -1）：最后添加的显示在第一行第一个
        min_order = await db.execute(
            select(func.min(UserBook.sort_order)).where(UserBook.user_id == user_id)
        )
        book = UserBook(
            user_id=user_id,
            title=data.title,
            author=data.author,
            format=data.format,
            size=data.size,
            chapter_count=data.chapter_count,
            has_preface=data.has_preface,
            sort_order=(min_order.scalar_one() or 0) - 1,
        )
        db.add(book)
        try:
            await db.commit()
            return book, True
        except IntegrityError:
            # 并发导入同名书的兜底：回滚后按已存在行处理
            await db.rollback()
            result = await db.execute(
                select(UserBook).where(UserBook.user_id == user_id, UserBook.title == data.title)
            )
            book = result.scalar_one()
            book.format = data.format
            book.size = data.size
            book.chapter_count = data.chapter_count
            book.has_preface = data.has_preface
            await db.commit()
            return book, False


    async def update_book(self, 
        db: AsyncSession, user_id: int, book_id: int, data: BookProgressUpdate
    ) -> UserBook | None:
        """
        阅读进度回写：任一进度字段出现即视作一次阅读（刷新 last_read_at）
        书籍不存在返回 None（路由层转 404）
        """
        book = await self.get_book(db, user_id, book_id)
        if book is None:
            return None
        touched = False
        if data.last_chapter is not None:
            book.last_chapter = data.last_chapter
            touched = True
        if data.last_page_index is not None:
            book.last_page_index = data.last_page_index
            touched = True
        if data.last_scroll_top is not None:
            book.last_scroll_top = data.last_scroll_top
            touched = True
        if data.last_percent is not None:
            book.last_percent = data.last_percent
            touched = True
        if data.pdf_ratio is not None:
            book.pdf_ratio = data.pdf_ratio
            touched = True
        if touched:
            book.last_read_at = TimezoneUtil.now()
            await db.commit()
        return book


    async def update_order(self, db: AsyncSession, user_id: int, data: BookOrderBatch) -> int:
        """批量更新书架手动排序（不存在的 id 跳过），返回实际更新行数"""
        updated = 0
        for item in data.items:
            result = await db.execute(
                select(UserBook).where(UserBook.id == item.id, UserBook.user_id == user_id)
            )
            book = result.scalar_one_or_none()
            if book is None:
                continue
            book.sort_order = item.sort_order
            updated += 1
        if updated > 0:
            await db.commit()
        return updated


    async def delete_book(self, db: AsyncSession, user_id: int, book_id: int) -> bool:
        """
        删除书籍（笔记/书签应用层级联），书籍不存在返回 False
        会话流水（reading_sessions）不随删清理：阅读历史属用户而非书籍，
        保留孤儿 book_id（按书统计经 join books 过滤，时段分析不受影响）
        """
        book = await self.get_book(db, user_id, book_id)
        if book is None:
            return False
        await db.execute(delete(ReadingNote).where(ReadingNote.book_id == book_id, ReadingNote.user_id == user_id))
        await db.execute(delete(ReadingBookmark).where(ReadingBookmark.book_id == book_id, ReadingBookmark.user_id == user_id))
        await db.delete(book)
        await db.commit()
        return True


    # ==================== 划线与想法 ====================

    @staticmethod
    def _flatten_ranges(ranges: list[list[int]] | None) -> list[int]:
        """区间对列表 → 扁平数组（传输层无嵌套数组，规避 uts2js 解析差异）"""
        flat: list[int] = []
        for pair in ranges or []:
            flat.extend(pair)
        return flat


    @staticmethod
    def underline_to_dict(note: ReadingNote) -> dict[str, Any]:
        return {"id": note.id, "cid": note.cid, "origin": note.origin, "ranges": ReadingService._flatten_ranges(note.ranges)}


    @staticmethod
    def thought_to_dict(note: ReadingNote) -> dict[str, Any]:
        return {
            "id": note.id,
            "from_cid": note.from_cid,
            "from_origin": note.from_origin,
            "from_start": note.from_start,
            "to_cid": note.to_cid,
            "to_origin": note.to_origin,
            "to_end": note.to_end,
            "quote": note.quote or "",
            "content": note.content or "",
        }


    async def list_notes(self, db: AsyncSession, user_id: int, book_id: int) -> dict[str, list[dict[str, Any]]] | None:
        """书籍的划线与想法列表（书籍不存在返回 None；虚拟书 0 为首页诗，直接放行）"""
        if book_id != VIRTUAL_BOOK_ID and await self.get_book(db, user_id, book_id) is None:
            return None
        result = await db.execute(
            select(ReadingNote)
            .where(ReadingNote.user_id == user_id, ReadingNote.book_id == book_id)
            .order_by(ReadingNote.id.asc())
        )
        notes = list(result.scalars().all())
        return {
            "underlines": [underline_to_dict(n) for n in notes if n.note_type == NOTE_TYPE_UNDERLINE],
            "thoughts": [thought_to_dict(n) for n in notes if n.note_type == NOTE_TYPE_THOUGHT],
        }


    async def upsert_underline(self, 
        db: AsyncSession, user_id: int, book_id: int, data: UnderlineUpsert
    ) -> dict[str, Any] | None:
        """
        划线按「章+段」upsert：ranges 空表示整段取消（删行），否则更新/写入
        返回 {id, deleted}；书籍不存在返回 None（虚拟书 0 为首页诗，直接放行）
        """
        if book_id != VIRTUAL_BOOK_ID and await self.get_book(db, user_id, book_id) is None:
            return None
        result = await db.execute(
            select(ReadingNote).where(
                ReadingNote.user_id == user_id,
                ReadingNote.book_id == book_id,
                ReadingNote.note_type == NOTE_TYPE_UNDERLINE,
                ReadingNote.cid == data.cid,
                ReadingNote.origin == data.origin,
            )
        )
        note = result.scalar_one_or_none()
        if len(data.ranges) == 0:
            if note is not None:
                await db.delete(note)
                await db.commit()
            return {"id": note.id if note is not None else 0, "deleted": True}
        # 扁平区间 → 区间对列表落库（与前端本地存储结构一致）
        pairs = [[data.ranges[i], data.ranges[i + 1]] for i in range(0, len(data.ranges), 2)]
        if note is None:
            note = ReadingNote(
                user_id=user_id,
                book_id=book_id,
                note_type=NOTE_TYPE_UNDERLINE,
                cid=data.cid,
                origin=data.origin,
                ranges=pairs,
            )
            db.add(note)
        else:
            note.ranges = pairs
        await db.commit()
        return {"id": note.id, "deleted": False}


    async def create_thought(self, 
        db: AsyncSession, user_id: int, book_id: int, data: ThoughtCreate
    ) -> dict[str, Any] | None:
        """写入想法（含划线文本快照），返回 {id}；书籍不存在返回 None（虚拟书 0 为首页诗，直接放行）"""
        if book_id != VIRTUAL_BOOK_ID and await self.get_book(db, user_id, book_id) is None:
            return None
        note = ReadingNote(
            user_id=user_id,
            book_id=book_id,
            note_type=NOTE_TYPE_THOUGHT,
            from_cid=data.from_cid,
            from_origin=data.from_origin,
            from_start=data.from_start,
            to_cid=data.to_cid,
            to_origin=data.to_origin,
            to_end=data.to_end,
            quote=data.quote,
            content=data.content,
        )
        db.add(note)
        await db.commit()
        return {"id": note.id}


    # ==================== 书签 ====================

    async def list_bookmarks(self, db: AsyncSession, user_id: int, book_id: int) -> list[dict[str, Any]] | None:
        """书签列表（书籍不存在返回 None）"""
        if await self.get_book(db, user_id, book_id) is None:
            return None
        result = await db.execute(
            select(ReadingBookmark)
            .where(ReadingBookmark.user_id == user_id, ReadingBookmark.book_id == book_id)
            .order_by(ReadingBookmark.chapter_id.asc(), ReadingBookmark.page_index.asc())
        )
        return [{"chapter_id": b.chapter_id, "page_index": b.page_index} for b in result.scalars().all()]


    async def replace_bookmarks(self, 
        db: AsyncSession, user_id: int, book_id: int, data: BookmarksReplace
    ) -> bool:
        """书签整表替换（前端本地列表即真源快照）；书籍不存在返回 False"""
        if await self.get_book(db, user_id, book_id) is None:
            return False
        await db.execute(
            delete(ReadingBookmark).where(ReadingBookmark.book_id == book_id, ReadingBookmark.user_id == user_id)
        )
        for item in data.items:
            db.add(ReadingBookmark(user_id=user_id, book_id=book_id, chapter_id=item.chapter_id, page_index=item.page_index))
        await db.commit()
        return True


    # ==================== 阅读时长 ====================

    async def _stats_pair(self, db: AsyncSession, user_id: int) -> tuple[int, int]:
        """(今日分钟数, 总分钟数)；当日无记录时该行不存在，须用 scalar_one_or_none 容错"""
        today = TimezoneUtil.today()
        today_row = await db.execute(
            select(ReadingDailyStat.minutes).where(ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today)
        )
        total_row = await db.execute(
            select(func.coalesce(func.sum(ReadingDailyStat.minutes), 0)).where(ReadingDailyStat.user_id == user_id)
        )
        return int(today_row.scalar_one_or_none() or 0), int(total_row.scalar_one() or 0)


    async def add_minutes(self, db: AsyncSession, user_id: int, minutes: int) -> dict[str, int]:
        """单次阅读结算累加（按东八区今日），返回累加后的今日与总分钟数"""
        today = TimezoneUtil.today()
        result = await db.execute(
            select(ReadingDailyStat).where(ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today)
        )
        row = result.scalar_one_or_none()
        if row is None:
            db.add(ReadingDailyStat(user_id=user_id, stat_date=today, minutes=minutes))
        else:
            row.minutes += minutes
        await db.commit()
        today_total, total = await self._stats_pair(db, user_id)
        return {"today_minutes": today_total, "total_minutes": total}


    async def get_stats(self, db: AsyncSession, user_id: int) -> dict[str, int]:
        """今日与累计阅读分钟数（书架统计卡/福利页用）"""
        today_total, total = await self._stats_pair(db, user_id)
        return {"today_minutes": today_total, "total_minutes": total}


    async def add_sessions(self, db: AsyncSession, user_id: int, data: SessionsReport) -> int:
        """
        批量写入阅读会话流水（按书/时段明细账，在线直传与离线补传共用）
        - 书籍不存在/非本人的条目跳过（离线期负数本地 id 未及迁移等场景），返回实际落库条数
        - 先集合查询合法书籍 id+title 防 N+1；title 落库为书名快照，删书后按书统计仍能展示
        - aggregate_minutes=True 的条目（离线补传，未经过分钟上报链路）按起算日（东八区，客户端
          本地时刻即东八区）聚合进 daily_stats；False 条目时长已由 /reading/minutes 计入不重复聚合
        """
        ids = {item.book_id for item in data.sessions}
        rows = await db.execute(
            select(UserBook.id, UserBook.title).where(UserBook.user_id == user_id, UserBook.id.in_(ids))
        )
        title_map = {row.id: row.title for row in rows.fetchall()}
        accepted = 0
        day_minutes: dict[date, int] = {}
        for item in data.sessions:
            if item.book_id not in title_map:
                continue
            started = datetime.strptime(item.started_at, "%Y-%m-%d %H:%M:%S")
            db.add(
                ReadingSession(
                    user_id=user_id,
                    book_id=item.book_id,
                    book_title=title_map[item.book_id],
                    source=item.source,
                    started_at=started,
                    ended_at=datetime.strptime(item.ended_at, "%Y-%m-%d %H:%M:%S"),
                    minutes=item.minutes,
                )
            )
            if item.aggregate_minutes:
                day = started.date()
                day_minutes[day] = day_minutes.get(day, 0) + item.minutes
            accepted += 1
        if accepted > 0:
            for day, mins in day_minutes.items():
                result = await db.execute(
                    select(ReadingDailyStat).where(
                        ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == day
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    db.add(ReadingDailyStat(user_id=user_id, stat_date=day, minutes=mins))
                else:
                    row.minutes += mins
            await db.commit()
        return accepted


    # ==================== 偏好 ====================

    async def get_prefs(self, db: AsyncSession, user_id: int) -> dict[str, Any] | None:
        """读取偏好配置（从未保存过返回 None，前端走本地默认）"""
        result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        row = result.scalar_one_or_none()
        return None if row is None else dict(row.prefs)


    async def put_prefs(self, db: AsyncSession, user_id: int, data: PrefsPut) -> dict[str, Any]:
        """偏好整包写入（upsert），返回写入后的配置"""
        result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        row = result.scalar_one_or_none()
        if row is None:
            row = UserPreference(user_id=user_id, prefs=data.prefs)
            db.add(row)
        else:
            row.prefs = data.prefs
        await db.commit()
        return dict(row.prefs)


    # ==================== 阅读报告（统计页） ====================

    REPORT_PERIODS = ("week", "month", "year", "total")

    # 时段偏好分段（按会话流水 started_at 小时归属，分钟和最大者作为偏好标签）
    _HOUR_SEGMENTS: list[tuple[str, int, int]] = [
        ("凌晨", 0, 5),
        ("上午", 6, 11),
        ("下午", 12, 17),
        ("夜间", 18, 23),
    ]


    @staticmethod
    def _month_range(anchor: date) -> tuple[date, date]:
        """锚点所在自然月的 (月初, 月末)"""
        start = anchor.replace(day=1)
        ny = start.year + (1 if start.month == 12 else 0)
        nm = 1 if start.month == 12 else start.month + 1
        return start, date(ny, nm, 1) - timedelta(days=1)


    async def get_report(self, db: AsyncSession, user_id: int, period: str, anchor: date) -> dict[str, Any]:
        """
        阅读统计报告（周期 = week 本周 / month 本月 / year 本年 / total 全部，anchor 为周期内锚点日期）
        - 趋势与时长来自 reading_daily_stats（聚合真源）；书籍榜与时段分布来自 reading_sessions（明细账，两账不保证一致）
        - 在读/完本为 user_books 累计状态（项目无按周期快照数据）；笔记数按 created_at 落区间统计
        """
        if period not in self.REPORT_PERIODS:
            raise ValueError("无效的统计周期")
        today = TimezoneUtil.today()

        # 周期区间与趋势点位（date, 坐标轴标签, 完整标签）
        points: list[tuple[date, str, str]] = []
        if period == "week":
            # 周日起始（轴序 日一二三四五六）
            start = anchor - timedelta(days=(anchor.weekday() + 1) % 7)
            end = start + timedelta(days=6)
            for i in range(7):
                d = start + timedelta(days=i)
                points.append((d, "日一二三四五六"[i], f"{d.month}月{d.day}日"))
        elif period == "month":
            start, end = self._month_range(anchor)
            for i in range((end - start).days + 1):
                d = start + timedelta(days=i)
                points.append((d, str(d.day), f"{d.day}日"))
        elif period == "year":
            start = date(anchor.year, 1, 1)
            end = date(anchor.year, 12, 31)
            for m in range(1, 13):
                points.append((date(anchor.year, m, 1), f"{m}月", f"{m}月"))
        else:  # total
            first = await db.execute(
                select(func.min(ReadingDailyStat.stat_date)).where(ReadingDailyStat.user_id == user_id)
            )
            first_date = first.scalar_one_or_none()
            start = first_date if first_date is not None else today
            end = today
            for y in range(start.year, end.year + 1):
                points.append((date(y, 1, 1), str(y), f"{y}年"))
        # 统计区间末裁剪到今天（未来日无数据，且避免日均被未到的天数稀释）；
        # 自然周期终点单独保留用于展示（周粒度选择器显示完整一周而非截至今天）
        natural_end = end
        end = min(end, today)
        day_start = datetime.combine(start, dtime.min)
        day_end = datetime.combine(end + timedelta(days=1), dtime.min)

        # 趋势：区间内每日分钟数按趋势点位聚合（week/month 逐日，year/total 按年）
        rows = await db.execute(
            select(ReadingDailyStat.stat_date, ReadingDailyStat.minutes).where(
                ReadingDailyStat.user_id == user_id,
                ReadingDailyStat.stat_date >= start,
                ReadingDailyStat.stat_date <= end,
            )
        )
        day_map = {r.stat_date: int(r.minutes) for r in rows.fetchall()}
        trend: list[dict[str, Any]] = []
        peak_minutes = 0
        peak_label = points[0][2] if points else ""
        for d, axis, full in points:
            if period in ("week", "month"):
                mins = day_map.get(d, 0)
            elif period == "year":
                # 年粒度按自然月分桶（点位为各月 1 日）
                mins = sum(v for k, v in day_map.items() if k.year == d.year and k.month == d.month)
            else:
                # 总粒度按自然年分桶
                mins = sum(v for k, v in day_map.items() if k.year == d.year)
            trend.append({"label": axis, "minutes": mins})
            if mins > peak_minutes:
                peak_minutes = mins
                peak_label = full
        total_minutes = sum(day_map.values())
        active_days = sum(1 for v in day_map.values() if v > 0)

        notes_row = await db.execute(
            select(func.count()).select_from(ReadingNote).where(
                ReadingNote.user_id == user_id,
                ReadingNote.created_at >= day_start,
                ReadingNote.created_at < day_end,
            )
        )

        # 书籍榜：周期内按书聚合时长 top3（book_title 快照支撑删书后展示）
        sess_where = (
            ReadingSession.user_id == user_id,
            ReadingSession.started_at >= day_start,
            ReadingSession.started_at < day_end,
        )
        total_rows = await db.execute(
            select(ReadingSession.book_title, func.sum(ReadingSession.minutes))
            .where(*sess_where)
            .group_by(ReadingSession.book_title)
            .order_by(desc(func.sum(ReadingSession.minutes)))
            .limit(3)
        )
        books = [
            {"book_title": t, "total_minutes": int(m)}
            for t, m in total_rows.fetchall()
        ]

        # 时段分布：0-23 点逐时聚合会话分钟数 + 偏好分段标签
        hour_rows = await db.execute(
            select(func.hour(ReadingSession.started_at), func.sum(ReadingSession.minutes))
            .where(*sess_where)
            .group_by(func.hour(ReadingSession.started_at))
        )
        hour_map = {int(h): int(m) for h, m in hour_rows.fetchall()}
        hours = [{"minutes": hour_map.get(h, 0)} for h in range(24)]
        peak_tag = ""
        best = 0
        for name, lo, hi in self._HOUR_SEGMENTS:
            s = sum(hour_map.get(h, 0) for h in range(lo, hi + 1))
            if s > best:
                best = s
                peak_tag = name

        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": natural_end.strftime("%Y-%m-%d"),
            "total_minutes": total_minutes,
            "avg_minutes": total_minutes // max((end - start).days + 1, 1),
            "active_days": active_days,
            "notes_count": int(notes_row.scalar_one()),
            "trend": trend,
            "peak": {"label": peak_label, "minutes": peak_minutes},
            "books": books,
            "hours": hours,
            "peak_tag": peak_tag,
        }


# 模块级单例
reading_service = ReadingService()
