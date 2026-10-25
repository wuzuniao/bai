from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .api import v1
from .core.auth_client import auth_client  # 模块级单例实例（勿导入模块本身）
from .core.config import settings
from .core.exceptions import BusinessError
from .core.response import response_service
from .services.share_cover_service import share_cover_service
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


async def _loop_cleanup_share_covers() -> None:
    """循环：清理超过 TTL 的转发封面临时文件（每日一轮，TTL 见 SHARE_COVER_TTL_DAYS）"""
    while True:
        try:
            removed = share_cover_service.cleanup_expired()
            if removed > 0:
                logger.info(f"转发封面清理完成：本轮删除 {removed} 个过期文件")
        except Exception:
            logger.exception("转发封面清理任务异常")
        await asyncio.sleep(24 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时预取 JWKS 公钥并拉起后台循环，关闭时停止"""
    # 启动即拉取一次 JWKS 公钥（磁盘+内存缓存），供 access_token 本地验签
    await auth_client.fetch_jwks()

    tasks: list[asyncio.Task] = []
    if settings.AUTH_SERVICE_TOKEN:
        tasks.append(asyncio.create_task(_loop_sync_revocations()))
        logger.info(
            "后台任务已启动：令牌撤销同步（间隔 "
            f"{settings.REVOCATION_SYNC_INTERVAL_SECONDS} 秒）"
        )
    else:
        logger.warning(
            "未配置 AUTH_SERVICE_TOKEN：跳过令牌撤销同步后台任务"
            "（受保护接口仍可本地验签，但改密/退出/删号后旧令牌残留至自然过期）"
        )
    tasks.append(asyncio.create_task(_loop_cleanup_share_covers()))
    logger.info(
        "后台任务已启动：转发封面临时目录清理（每日一轮，TTL "
        f"{settings.SHARE_COVER_TTL_DAYS} 天）"
    )
    yield
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass


# 接口文档开关：开发默认开启；生产由部署脚本生成的 .env 置 DOCS_ENABLED=false，
# 关闭 /docs /redoc /openapi.json（公网不暴露接口清单；nginx 层亦只反代 /api/ 与 /health）
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # 本地开发源放行（任意 localhost/127.0.0.1 端口）：H5 开发服务器端口不固定
    # （HBuilderX 默认 8080、Vite 5173 等），逐一登记易漏；经 CORS_ALLOW_LOCALHOST
    # 控制——开发 true / 生产部署脚本置 false（与 DOCS_ENABLED 同模式）
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if settings.CORS_ALLOW_LOCALHOST else None
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ==================== 请求日志中间件 ====================


class RequestLoggingMiddleware:
    """请求日志（纯 ASGI 实现，避免 BaseHTTPMiddleware 对非 http scope 的副作用）：
    方法/路径/状态码/耗时，健康检查端点不记录"""

    SKIP_PATHS = ("/", "/health")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return
        start = perf_counter()
        status_holder: dict[str, Any] = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            cost_ms = (perf_counter() - start) * 1000
            logger.info(
                f"{scope['method']} {scope['path']} -> {status_holder['status']} ({cost_ms:.1f}ms)"
            )


app.add_middleware(RequestLoggingMiddleware)


# ==================== 统一异常处理（错误体与成功体结构一致：{code, msg, data}） ====================


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTPException 统一包装：status 与 code 同值，msg 取 detail（不暴露内部细节由路由层保证）"""
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} {request.url.path}: {detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=response_service.error(exc.status_code, detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """参数校验失败（422）：msg 面向用户不暴露字段内部细节，明细记日志排查"""
    logger.warning(f"参数校验失败 {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content=response_service.error(422, "请求参数格式不正确"),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    业务校验失败兜底转 400（规范约定 ValueError 系=业务错误；路由层已转的不会走到这里）
    - BusinessError：文案面向用户，直接回显
    - 非 BusinessError 的原生 ValueError（库层 int()/datetime 解析等）：内部解析细节
      不外泄，对外输出固定文案，真实异常记日志排查
    """
    if isinstance(exc, BusinessError):
        msg = str(exc) or "请求参数不正确"
        logger.warning(f"业务校验失败 {request.method} {request.url.path}: {msg}")
    else:
        msg = "请求参数不正确"
        logger.warning(
            f"非业务 ValueError（对外固定文案）{request.method} {request.url.path}: {exc!r}"
        )
    return JSONResponse(
        status_code=400,
        content=response_service.error(400, msg),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未预期异常兜底（500）：记录完整堆栈到 app.log，对外不泄露内部细节"""
    logger.exception(f"未处理异常 {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content=response_service.error(500, "服务异常，请稍后重试"),
    )


app.include_router(v1.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
