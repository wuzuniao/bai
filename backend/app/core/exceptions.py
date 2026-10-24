"""
业务异常定义（BusinessError：业务校验失败的统一异常类型）
--------------------------------------------------------------------------
- 继承 ValueError：兼容路由层既有「except ValueError → 400」捕获与项目规范的
  ValueError 约定，服务层抛出、路由层捕获的代码均无需感知子类化
- 与原生 ValueError 的区别：main.py 的 ValueError 兜底处理器只回显
  BusinessError 的异常文案（面向用户）；库层抛出的原生 ValueError
  （如 int()/datetime 解析失败）对外输出固定文案，避免内部解析细节泄露
"""

from __future__ import annotations


class BusinessError(ValueError):
    """业务校验失败（异常文案面向用户，可直接回显给客户端）"""
