from __future__ import annotations

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
    CORS_ALLOW_ORIGINS: str = "https://bai.wuzuniao.com"

    # 是否放行本地开发源（任意 localhost/127.0.0.1 端口）：H5 开发服务器端口不固定
    # （HBuilderX 默认 8080、Vite 5173 等），逐一登记易漏故用正则统一放行；
    # 生产部署脚本生成的 .env 置 false（本地源放行仅开发联调需要，生产不应保留）
    CORS_ALLOW_LOCALHOST: bool = True

    # 接口文档开关（/docs /redoc /openapi.json）：开发默认开启；生产部署脚本生成的
    # .env 置 false（公网不暴露接口清单；nginx 层亦只反代 /api/ 与 /health，双保险）
    DOCS_ENABLED: bool = True

    # 微信小程序配置（预留：业务功能使用微信能力时启用）
    WX_APPID: str = ""
    WX_APP_SECRET: str = ""

    # ==================== 腾讯云 COS 对象存储（书籍文件云端同步） ====================
    # 永久密钥仅存后端：经 STS GetFederationToken 换取按用户目录隔离的临时密钥，
    # 再生成预签名 URL 下发前端直传/下载，临时凭证同样不出后端
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""
    COS_BUCKET: str = ""  # 桶全名（形如 bai-books-1253379498）
    COS_REGION: str = "ap-guangzhou"
    COS_APPID: str = ""  # 腾讯云 APPID（Policy 资源六段式 uid 段）
    COS_CRED_SECONDS: int = 1800  # STS 临时凭证有效期（秒）
    # 自定义源站域名（如 bai-books.wuzuniao.com，须已在 COS 控制台绑定桶并配 HTTPS 证书；
    # 留空回退桶默认域名。COS 签名不含 Host 头，换域名不影响预签名校验）
    COS_CUSTOM_DOMAIN: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """解析 CORS_ALLOW_ORIGINS 为列表（去除空白与重复项）"""
        return list(
            dict.fromkeys(
                origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()
            )
        )

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        extra="allow",
    )


settings = Settings()
