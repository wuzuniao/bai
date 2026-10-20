"""
统一响应实体（ResponseService：全部接口 {code, msg, data} 包装唯一出口）
--------------------------------------------------------------------------
- 成功：code=0，msg="success"，data 为业务数据（可为 None）
- 错误：code=HTTP 状态码语义（400/401/403/404/422/429/500），msg 面向用户
- 路由层经 response_service.ok() 包装成功响应；异常处理器（main.py）经
  error() 包装错误响应，保证错误体与成功体结构一致（前端统一按 code/msg 解析）

用法：
    from ...core.response import response_service

    return response_service.ok(await svc.get_summary(db, user_id))
"""
from __future__ import annotations

from typing import Any


class ResponseService:
    """统一响应包装服务"""

    #: 业务成功码
    SUCCESS_CODE = 0
    #: 成功文案
    SUCCESS_MSG = "success"

    @classmethod
    def ok(cls, data: Any = None) -> dict[str, Any]:
        """成功响应包装 {code: 0, msg: "success", data}"""
        return {"code": cls.SUCCESS_CODE, "msg": cls.SUCCESS_MSG, "data": data}

    @classmethod
    def error(cls, code: int, msg: str, data: Any = None) -> dict[str, Any]:
        """错误响应包装 {code, msg, data}（供异常处理器统一错误体结构）"""
        return {"code": code, "msg": msg, "data": data}


# 模块级单例
response_service = ResponseService()
