"""云端同步接口校验模型（COS 书籍直传/下载/删除）"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from ..core.sanitizer import SecuritySanitizer


class CloudBookRequest(BaseModel):
    """云端同步书籍参数（书名 + 格式；对象 key 由服务端按用户目录拼装，前端不可传路径）"""

    title: str
    format: str

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = SecuritySanitizer.clean_text(v, max_length=200)
        if not v:
            raise ValueError("书名不能为空")
        return v

    @field_validator("format", mode="before")
    @classmethod
    def validate_format(cls, v: str) -> str:
        v = SecuritySanitizer.clean_text(v, max_length=10).lower()
        if v not in ("txt", "pdf"):
            raise ValueError("仅支持 txt / pdf 格式书籍同步")
        return v
