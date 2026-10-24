"""
数据库基础设施（SQLAlchemy 2.0 异步 + asyncmy，面向对象：Database 类 + 模块级单例）
--------------------------------------------------------------------------
- 引擎按 backend/.env 的 DATABASE_URL 创建；连接初始化统一设置东八区时区
- 隔离级别 READ COMMITTED：进度/排序/笔记写点均为「读最新→改→提交」短事务，
  默认 REPEATABLE READ 下并发回写同一行会报 1020（Record has changed since last read）
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


class Database:
    """数据库引擎与会话工厂封装（请求级会话随请求结束关闭）"""

    def __init__(self, url: str) -> None:
        self.engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=3600,
            isolation_level="READ COMMITTED",
            connect_args={"init_command": "SET time_zone='+08:00'"},
        )
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI 依赖：请求级数据库会话（随请求结束关闭）"""
        async with self.session_factory() as session:
            yield session


# 模块级单例（get_db 依赖函数与 SessionLocal 别名保持既有导入路径可用）
database = Database(settings.DATABASE_URL)
SessionLocal = database.session_factory
get_db = database.get_db
