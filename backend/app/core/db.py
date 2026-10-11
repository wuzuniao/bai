"""
数据库基础设施（SQLAlchemy 2.0 异步 + asyncmy）
--------------------------------------------------------------------------
- 引擎按 backend/.env 的 DATABASE_URL 创建；连接初始化统一设置东八区时区
- 建表统一由 backend/sql/ 原始脚本管理，本模块仅承载 ORM 映射与请求级会话

用法：
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from .core.db import get_db

    @router.get("/demo")
    async def demo(db: AsyncSession = Depends(get_db)):
        ...
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """ORM 声明基类（表结构真源在 backend/sql/，模型仅做映射）"""


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"init_command": "SET time_zone='+08:00'"},
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级数据库会话（随请求结束关闭）"""
    async with SessionLocal() as session:
        yield session
