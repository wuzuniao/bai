import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import v1
from .core import auth_client
from .core.config import settings
from .utils.logger import logger


async def _loop_sync_revocations() -> None:
    """
    循环：拉取 auth 服务的令牌撤销增量（「本地验签 + 后台撤销同步」的同步侧）
    - 每轮调用 auth_client.pull_revocations，合并 {user_id: 撤销时刻} 本地状态
    - deps 每请求经 is_revoked 本地比对 iat，零网络调用
    - 拉取失败保留旧水位下一轮重试（容忍 auth 短暂不可达）
    """
    while True:
        try:
            added = await auth_client.pull_revocations()
            if added > 0:
                logger.info(f"令牌撤销同步完成：本轮新增 {added} 条撤销记录")
        except Exception:
            logger.exception("令牌撤销同步任务异常")
        await asyncio.sleep(settings.REVOCATION_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时预取 JWKS 公钥并拉起后台循环，关闭时停止"""
    # 启动即拉取一次 JWKS 公钥（磁盘+内存缓存），供 access_token 本地验签
    await auth_client.fetch_jwks()

    tasks: list[asyncio.Task] = []
    if settings.AUTH_SERVICE_TOKEN:
        tasks = [asyncio.create_task(_loop_sync_revocations())]
        logger.info(
            "后台任务已启动：令牌撤销同步（间隔 "
            f"{settings.REVOCATION_SYNC_INTERVAL_SECONDS} 秒）"
        )
    else:
        logger.warning(
            "未配置 AUTH_SERVICE_TOKEN：跳过令牌撤销同步后台任务"
            "（受保护接口仍可本地验签，但改密/退出/删号后旧令牌残留至自然过期）"
        )
    yield
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(v1.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
