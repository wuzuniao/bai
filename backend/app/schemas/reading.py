"""
阅读业务 Pydantic 校验模型（校验逻辑集中本层，路由不散写）
--------------------------------------------------------------------------
- 字段命名与接口 JSON 保持 snake_case（与 auth/项目既有接口风格一致）
- 必填项缺失/越界由 Pydantic 抛 422，业务规则错误由服务层抛 ValueError 转 400
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BookCreate(BaseModel):
    """导入登记（POST /books；同用户同名复用已有行，仅回填元数据）"""

    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=100)
    format: str = Field(description="TXT / PDF")
    size: int = Field(default=0, ge=0, le=2**31)
    chapter_count: int = Field(default=0, ge=0, le=100000)
    has_preface: bool = False

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ("TXT", "PDF"):
            raise ValueError("format 仅支持 TXT / PDF")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("书名不能为空")
        return v


class BookProgressUpdate(BaseModel):
    """阅读进度回写（PUT /books/{id}；任一进度字段出现即视作一次阅读，刷新 last_read_at）"""

    last_chapter: int | None = Field(default=None, ge=-1, le=100000)
    last_page_index: int | None = Field(default=None, ge=0, le=1000000)
    last_scroll_top: int | None = Field(default=None, ge=0, le=10**9)
    last_percent: int | None = Field(default=None, ge=0, le=100)
    pdf_ratio: float | None = Field(default=None, ge=0, le=100)


class BookOrderItem(BaseModel):
    """书架手动排序单项"""

    id: int = Field(gt=0)
    sort_order: int = Field(ge=0, le=1000000)


class BookOrderBatch(BaseModel):
    """书架手动排序批量（拖拽落定一次提交全部受影响行）"""

    items: list[BookOrderItem] = Field(min_length=1, max_length=1000)


class UnderlineUpsert(BaseModel):
    """划线按「章+段」upsert（ranges 为扁平数组 [s1,e1,s2,e2,...]；空数组=整段划线取消，删除该行）"""

    cid: int = Field(ge=0, le=100000)
    origin: int = Field(ge=0, le=1000000)
    ranges: list[int] = Field(max_length=200)

    @field_validator("ranges")
    @classmethod
    def validate_ranges(cls, v: list[int]) -> list[int]:
        if len(v) % 2 != 0:
            raise ValueError("划线扁平区间长度须为偶数")
        for i in range(0, len(v), 2):
            if v[i] < 0 or v[i + 1] < v[i] or v[i + 1] > 10**7:
                raise ValueError("划线区间须满足 start <= end")
        return v


class ThoughtCreate(BaseModel):
    """想法写入（跨章选区定位 + 划线文本快照 + 正文）"""

    from_cid: int = Field(ge=0, le=100000)
    from_origin: int = Field(ge=0, le=1000000)
    from_start: int = Field(ge=0, le=10**7)
    to_cid: int = Field(ge=0, le=100000)
    to_origin: int = Field(ge=0, le=1000000)
    to_end: int = Field(ge=0, le=10**7)
    quote: str = Field(default="", max_length=65535)
    content: str = Field(min_length=1, max_length=65535)


class BookmarkItem(BaseModel):
    """书签单项"""

    chapter_id: int = Field(ge=0, le=100000)
    page_index: int = Field(ge=0, le=1000000)


class BookmarksReplace(BaseModel):
    """书签整表替换（前端本地书签列表即真源快照，PUT 全量覆盖）"""

    items: list[BookmarkItem] = Field(max_length=1000)


class MinutesReport(BaseModel):
    """阅读时长上报（单次结算分钟数，服务端按东八区今日累加）"""

    minutes: int = Field(ge=1, le=1440)


class PrefsPut(BaseModel):
    """偏好配置整包写入（键值集由前端定义，后端不感知内部结构）"""

    prefs: dict = Field(max_length=100)
