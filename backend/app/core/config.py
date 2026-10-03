from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（config.py 位于 backend/app/core/），用于按绝对路径定位 .env 文件
_BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    PROJECT_NAME: str = "无足鸟古诗词学习助手"
    API_V1_STR: str = "/api/v1"

    # ==================== auth 统一认证服务配置 ====================
    # auth 服务基础地址（调用其 /internal/* 接口时使用）
    # 开发环境：http://localhost:11000；生产环境：https://auth.wuzuniao.com
    AUTH_BASE_URL: str = "https://auth.wuzuniao.com"
    # 令牌签发方标识（须与 auth 服务 .env 的 ISSUER 完全一致，否则验签不通过）
    AUTH_ISSUER: str = "https://auth.wuzuniao.com"
    # 服务间通信令牌（调用 auth /internal/* 时携带的 X-Service-Token；
    # 与 auth 服务 .env 的 SERVICE_TOKEN 一致）
    AUTH_SERVICE_TOKEN: str = ""
    # 本项目在 auth oauth_clients 表登记的第一方 client_id
    # （前端登录类请求显式携带，auth 按此签发本项目认识的 identity id 令牌；
    #   旧版「删号上报 purge-report 携带」用途已随账号别名与合并改造废除）
    AUTH_CLIENT_ID: str = "bai"
    # 令牌撤销增量同步间隔（秒）：后台循环每该间隔拉取一次 auth 的撤销日志，
    # 决定「改密码/退出/删号后旧令牌在本服务的最大残留窗口」
    REVOCATION_SYNC_INTERVAL_SECONDS: int = 300

    # CORS 允许的源（逗号分隔；小程序/App 请求不携带 Origin，不受 CORS 限制）
    CORS_ALLOW_ORIGINS: str = "https://bai.wuzuniao.com,http://localhost:5173"

    # 微信小程序配置（预留：业务功能使用微信能力时启用）
    WX_APPID: str = ""
    WX_APP_SECRET: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """解析 CORS_ALLOW_ORIGINS 为列表（去除空白与重复项）"""
        return list(dict.fromkeys(
            origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()
        ))

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        extra="allow",
    )


settings = Settings()
