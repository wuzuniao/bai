from fastapi import APIRouter

from . import books, preferences, reading, users

# v1 接口聚合路由（main.py 挂载于 /api/v1 前缀）
router = APIRouter()
router.include_router(users.router)
router.include_router(books.router)
router.include_router(reading.router)
router.include_router(preferences.router)
