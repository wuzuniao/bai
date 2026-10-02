from fastapi import APIRouter

from . import users

# v1 接口聚合路由（main.py 挂载于 /api/v1 前缀）
router = APIRouter()
router.include_router(users.router)
