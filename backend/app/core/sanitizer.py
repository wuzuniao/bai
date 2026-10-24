"""
输入安全清洗器（SecuritySanitizer：全部接口入库文本值的统一清洗入口）
--------------------------------------------------------------------------
设计：
- 清洗项：控制字符（C0/C1/DEL）、零宽与不可见字符、首尾空白、超长截断
- 不做 HTML 转义：本端为原生渲染（uvue text 不解析 HTML），入库转义反而造成
  「&amp;」等二次显示问题；防注入由参数化查询（SQLAlchemy）承担，本类专注
  字符净化与长度收口（纵深防御）
- 接入方式：Pydantic schema 的 @field_validator 内调用（校验逻辑集中 schema 层，
  路由与服务层不再散写清洗）；自由 dict（偏好键值）经 clean_dict 递归净化

用法：
    from ..core.sanitizer import SecuritySanitizer

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = SecuritySanitizer.clean_text(v, max_length=200)
        if not v:
            raise ValueError("书名不能为空")
        return v
"""

from __future__ import annotations

import re
from typing import Any

# 控制字符（C0；清洗时保留换行，由 multiline 参数决定去留）与 DEL/C1
_CONTROL_RE = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")
# 换行符（单行字段清洗用）
_NEWLINE_RE = re.compile(r"[\r\n]+")
# 零宽与不可见字符：零宽空格/连接符、双向控制、变体选择符补集、BOM、交互符号
_INVISIBLE_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\ufff9-\ufffb]")


class SecuritySanitizer:
    """接口输入值安全清洗器（文本净化 + 长度收口 + 自由 dict 递归净化）"""

    #: 自由 dict（偏好键值）净化的默认安全边界
    MAX_DICT_DEPTH = 4
    MAX_DICT_ITEMS = 100
    MAX_DICT_STR_LEN = 512

    @classmethod
    def clean_text(cls, value: str, *, max_length: int, multiline: bool = False) -> str:
        """
        文本清洗：剥离控制/零宽字符 → 压平换行（单行字段）→ 去首尾空白 → 截断
        :param value: 原始输入（None 安全处理为空串）
        :param max_length: 最大长度（Unicode 字符数，超出截断）
        :param multiline: False 时将换行压平为空格（标题/书名等单行字段）
        :return: 清洗后的文本
        """
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        cleaned = _CONTROL_RE.sub("", value)
        if multiline:
            cleaned = _NEWLINE_RE.sub("\n", cleaned)
        else:
            cleaned = _NEWLINE_RE.sub(" ", cleaned)
        cleaned = _INVISIBLE_RE.sub("", cleaned)
        return cleaned.strip()[:max_length]

    @classmethod
    def clean_dict(
        cls,
        value: Any,
        *,
        max_depth: int | None = None,
        max_items: int | None = None,
        max_str_len: int | None = None,
    ) -> Any:
        """
        自由键值结构递归净化（偏好整包等后端不感知内部结构的 dict）
        - 字符串值逐个 clean_text；数字/布尔/null 原样保留；dict/list 递归
        - 超出深度/条目数限制、含不支持类型（二进制/对象等）抛 ValueError → 400
        """
        depth = cls.MAX_DICT_DEPTH if max_depth is None else max_depth
        items = cls.MAX_DICT_ITEMS if max_items is None else max_items
        str_len = cls.MAX_DICT_STR_LEN if max_str_len is None else max_str_len

        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return cls.clean_text(value, max_length=str_len, multiline=True)
        if isinstance(value, dict):
            if depth <= 0:
                raise ValueError("配置嵌套层级超出限制")
            if len(value) > items:
                raise ValueError("配置条目数超出限制")
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                cleaned_key = cls.clean_text(str(key), max_length=64)
                if not cleaned_key:
                    raise ValueError("配置键名不能为空")
                cleaned[cleaned_key] = cls.clean_dict(
                    item, max_depth=depth - 1, max_items=items, max_str_len=str_len
                )
            return cleaned
        if isinstance(value, list):
            if len(value) > items:
                raise ValueError("配置条目数超出限制")
            return [
                cls.clean_dict(item, max_depth=depth - 1, max_items=items, max_str_len=str_len)
                for item in value
            ]
        raise ValueError("配置包含不支持的值类型")
