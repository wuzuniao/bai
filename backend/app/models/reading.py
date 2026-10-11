"""
阅读业务 ORM 模型（表结构真源见 backend/sql/create_bai_db.sql）
--------------------------------------------------------------------------
- 书籍正文文件不落库（仅存用户端沙盒），本组模型只承载元数据
- 外键不设物理约束（项目规范），书籍删除时笔记/书签由应用层级联清理
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BIGINT, DATE, TEXT, VARCHAR, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import DECIMAL, JSON, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class UserBook(Base):
    """用户书籍元数据（同用户书名唯一，重导入同名书复用同一行）"""

    __tablename__ = "user_books"
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uk_ub_user_title"),
        Index("idx_user_books_lastread", "user_id", "last_read_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False, comment="业务用户 id（JWT sub）")
    title: Mapped[str] = mapped_column(VARCHAR(200), nullable=False, comment="书名")
    author: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, default="", server_default="", comment="作者")
    format: Mapped[str] = mapped_column(VARCHAR(10), nullable=False, comment="TXT / PDF")
    size: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0, server_default="0", comment="文件字节数")
    chapter_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="章节数（PDF=页数）")
    has_preface: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=False, server_default="0", comment="txt 序章存在性")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="书架手动排序（越小越前）")
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, comment="最近阅读时刻（NULL=未读）")
    last_chapter: Mapped[int] = mapped_column(nullable=False, default=-1, server_default="-1", comment="最近章 id（-1=未读）")
    last_page_index: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="章内页码 0-based")
    last_scroll_top: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="滚动位置 px")
    last_percent: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="阅读百分比 0-100（仅 PDF）")
    pdf_ratio: Mapped[float] = mapped_column(DECIMAL(10, 4), nullable=False, default=0, server_default="0", comment="PDF 首页高/宽比")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class ReadingNote(Base):
    """阅读划线与想法（合一：note_type 区分，划线/想法各自维护定位字段）"""

    __tablename__ = "reading_notes"
    __table_args__ = (
        Index("idx_rn_user_book", "user_id", "book_id", "note_type", "cid", "origin"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    book_id: Mapped[int] = mapped_column(BIGINT, nullable=False, comment="所属书籍（user_books.id）")
    note_type: Mapped[int] = mapped_column(TINYINT(1), nullable=False, comment="0=划线 1=想法")
    # 划线定位（type=0）
    cid: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="划线章 id")
    origin: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="划线段索引")
    ranges: Mapped[list[list[int]] | None] = mapped_column(JSON, nullable=True, comment="段内字符闭区间")
    # 想法选区（type=1，跨章起点/终点）
    from_cid: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="选区起点章 id")
    from_origin: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    from_start: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    to_cid: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="选区终点章 id")
    to_origin: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    to_end: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    quote: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="划线文本快照（type=1）")
    content: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="想法正文（type=1）")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class ReadingBookmark(Base):
    """阅读书签（章 + 章内页码定位）"""

    __tablename__ = "reading_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "chapter_id", "page_index", name="uk_rb_pos"),
        Index("idx_rb_user_book", "user_id", "book_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    book_id: Mapped[int] = mapped_column(BIGINT, nullable=False, comment="所属书籍（user_books.id）")
    chapter_id: Mapped[int] = mapped_column(nullable=False, comment="章 id")
    page_index: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="章内页码 0-based")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class ReadingDailyStat(Base):
    """每日阅读时长统计（按日 upsert 累加）"""

    __tablename__ = "reading_daily_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "stat_date", name="uk_rds_user_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    stat_date: Mapped[date] = mapped_column(DATE, nullable=False, comment="统计日期（东八区）")
    minutes: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", comment="当日累计阅读分钟数")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )


class UserPreference(Base):
    """用户阅读偏好（单行 JSON：阅读设置 + 书架样式）"""

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_up_user"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    prefs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="偏好配置 JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate=datetime.now
    )
