"""
阅读业务服务层（书籍元数据 / 笔记 / 书签 / 时长 / 偏好）
--------------------------------------------------------------------------
- 全部按 user_id 隔离查询；书籍不存在等资源缺失由调用方（路由层）判空转 404
- 业务规则错误抛 ValueError（路由层统一转 400）
- 时间统一东八区（数据库会话已 SET time_zone='+08:00'，此处写入 naive 东八区值）
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ReadingBookmark, ReadingDailyStat, ReadingNote, UserBook, UserPreference
from ..schemas.reading import (
    BookCreate,
    BookmarksReplace,
    BookOrderBatch,
    BookProgressUpdate,
    PrefsPut,
    ThoughtCreate,
    UnderlineUpsert,
)

TZ_CN = timezone(timedelta(hours=8))

# 书籍删除时应用层级联清理的子资源（外键不设物理约束，规范约定）
NOTE_TYPE_UNDERLINE = 0
NOTE_TYPE_THOUGHT = 1

# 首页诗词《无题》虚拟书 id：内容全局固定，无 user_books 行（不进书架、无进度），
# 划线/想法以 book_id=0 落 reading_notes，按 user_id 天然隔离；坐标约定 cid=0 唯一章、
# origin=诗行序号（0-15）、字符区间含行尾标点（每行 7 字 + 标点共 8 位）
VIRTUAL_BOOK_ID = 0


def now_cn() -> datetime:
    """当前东八区时刻（naive，与 DATETIME 列对齐）"""
    return datetime.now(TZ_CN).replace(tzinfo=None)


def today_cn() -> date:
    """当前东八区日期"""
    return datetime.now(TZ_CN).date()


def fmt_dt(dt: datetime | None) -> str | None:
    """DATETIME → 接口时间格式（YYYY-MM-DD HH:mm:ss）"""
    return None if dt is None else dt.strftime("%Y-%m-%d %H:%M:%S")


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
        "last_read_at": fmt_dt(book.last_read_at),
        "last_chapter": book.last_chapter,
        "last_page_index": book.last_page_index,
        "last_scroll_top": book.last_scroll_top,
        "last_percent": book.last_percent,
        "pdf_ratio": float(book.pdf_ratio),
        "created_at": fmt_dt(book.created_at),
        "updated_at": fmt_dt(book.updated_at),
    }


async def get_book(db: AsyncSession, user_id: int, book_id: int) -> UserBook | None:
    """按 id 取当前用户的书籍（不存在/非本人返回 None）"""
    result = await db.execute(
        select(UserBook).where(UserBook.id == book_id, UserBook.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_books(db: AsyncSession, user_id: int) -> list[UserBook]:
    """书架列表（按手动排序序返回，本地缓存顺序即该顺序）"""
    result = await db.execute(
        select(UserBook)
        .where(UserBook.user_id == user_id)
        .order_by(UserBook.sort_order.asc(), UserBook.id.asc())
    )
    return list(result.scalars().all())


async def register_book(db: AsyncSession, user_id: int, data: BookCreate) -> tuple[UserBook, bool]:
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


async def update_book(
    db: AsyncSession, user_id: int, book_id: int, data: BookProgressUpdate
) -> UserBook | None:
    """
    阅读进度回写：任一进度字段出现即视作一次阅读（刷新 last_read_at）
    书籍不存在返回 None（路由层转 404）
    """
    book = await get_book(db, user_id, book_id)
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
        book.last_read_at = now_cn()
        await db.commit()
    return book


async def update_order(db: AsyncSession, user_id: int, data: BookOrderBatch) -> int:
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


async def delete_book(db: AsyncSession, user_id: int, book_id: int) -> bool:
    """删除书籍（笔记/书签应用层级联），书籍不存在返回 False"""
    book = await get_book(db, user_id, book_id)
    if book is None:
        return False
    await db.execute(delete(ReadingNote).where(ReadingNote.book_id == book_id, ReadingNote.user_id == user_id))
    await db.execute(delete(ReadingBookmark).where(ReadingBookmark.book_id == book_id, ReadingBookmark.user_id == user_id))
    await db.delete(book)
    await db.commit()
    return True


# ==================== 划线与想法 ====================

def _flatten_ranges(ranges: list[list[int]] | None) -> list[int]:
    """区间对列表 → 扁平数组（传输层无嵌套数组，规避 uts2js 解析差异）"""
    flat: list[int] = []
    for pair in ranges or []:
        flat.extend(pair)
    return flat


def underline_to_dict(note: ReadingNote) -> dict[str, Any]:
    return {"id": note.id, "cid": note.cid, "origin": note.origin, "ranges": _flatten_ranges(note.ranges)}


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


async def list_notes(db: AsyncSession, user_id: int, book_id: int) -> dict[str, list[dict[str, Any]]] | None:
    """书籍的划线与想法列表（书籍不存在返回 None；虚拟书 0 为首页诗，直接放行）"""
    if book_id != VIRTUAL_BOOK_ID and await get_book(db, user_id, book_id) is None:
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


async def upsert_underline(
    db: AsyncSession, user_id: int, book_id: int, data: UnderlineUpsert
) -> dict[str, Any] | None:
    """
    划线按「章+段」upsert：ranges 空表示整段取消（删行），否则更新/写入
    返回 {id, deleted}；书籍不存在返回 None（虚拟书 0 为首页诗，直接放行）
    """
    if book_id != VIRTUAL_BOOK_ID and await get_book(db, user_id, book_id) is None:
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


async def create_thought(
    db: AsyncSession, user_id: int, book_id: int, data: ThoughtCreate
) -> dict[str, Any] | None:
    """写入想法（含划线文本快照），返回 {id}；书籍不存在返回 None（虚拟书 0 为首页诗，直接放行）"""
    if book_id != VIRTUAL_BOOK_ID and await get_book(db, user_id, book_id) is None:
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

async def list_bookmarks(db: AsyncSession, user_id: int, book_id: int) -> list[dict[str, Any]] | None:
    """书签列表（书籍不存在返回 None）"""
    if await get_book(db, user_id, book_id) is None:
        return None
    result = await db.execute(
        select(ReadingBookmark)
        .where(ReadingBookmark.user_id == user_id, ReadingBookmark.book_id == book_id)
        .order_by(ReadingBookmark.chapter_id.asc(), ReadingBookmark.page_index.asc())
    )
    return [{"chapter_id": b.chapter_id, "page_index": b.page_index} for b in result.scalars().all()]


async def replace_bookmarks(
    db: AsyncSession, user_id: int, book_id: int, data: BookmarksReplace
) -> bool:
    """书签整表替换（前端本地列表即真源快照）；书籍不存在返回 False"""
    if await get_book(db, user_id, book_id) is None:
        return False
    await db.execute(
        delete(ReadingBookmark).where(ReadingBookmark.book_id == book_id, ReadingBookmark.user_id == user_id)
    )
    for item in data.items:
        db.add(ReadingBookmark(user_id=user_id, book_id=book_id, chapter_id=item.chapter_id, page_index=item.page_index))
    await db.commit()
    return True


# ==================== 阅读时长 ====================

async def _stats_pair(db: AsyncSession, user_id: int) -> tuple[int, int]:
    """(今日分钟数, 总分钟数)；当日无记录时该行不存在，须用 scalar_one_or_none 容错"""
    today = today_cn()
    today_row = await db.execute(
        select(ReadingDailyStat.minutes).where(ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today)
    )
    total_row = await db.execute(
        select(func.coalesce(func.sum(ReadingDailyStat.minutes), 0)).where(ReadingDailyStat.user_id == user_id)
    )
    return int(today_row.scalar_one_or_none() or 0), int(total_row.scalar_one() or 0)


async def add_minutes(db: AsyncSession, user_id: int, minutes: int) -> dict[str, int]:
    """单次阅读结算累加（按东八区今日），返回累加后的今日与总分钟数"""
    today = today_cn()
    result = await db.execute(
        select(ReadingDailyStat).where(ReadingDailyStat.user_id == user_id, ReadingDailyStat.stat_date == today)
    )
    row = result.scalar_one_or_none()
    if row is None:
        db.add(ReadingDailyStat(user_id=user_id, stat_date=today, minutes=minutes))
    else:
        row.minutes += minutes
    await db.commit()
    today_total, total = await _stats_pair(db, user_id)
    return {"today_minutes": today_total, "total_minutes": total}


async def get_stats(db: AsyncSession, user_id: int) -> dict[str, int]:
    """今日与累计阅读分钟数（书架统计卡/福利页用）"""
    today_total, total = await _stats_pair(db, user_id)
    return {"today_minutes": today_total, "total_minutes": total}


# ==================== 偏好 ====================

async def get_prefs(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
    """读取偏好配置（从未保存过返回 None，前端走本地默认）"""
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    row = result.scalar_one_or_none()
    return None if row is None else dict(row.prefs)


async def put_prefs(db: AsyncSession, user_id: int, data: PrefsPut) -> dict[str, Any]:
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
