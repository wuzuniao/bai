"""
时区工具模块
--------------------------------------------------------------------------
统一项目时区为上海时区（UTC+8），确保时间数据在存储、传输和展示过程中保持一致。

设计原则：
- 数据库 DATETIME 列存储无时区的上海时间（naive datetime）
- Python 代码中使用 now_shanghai() 获取当前上海时间
- API 响应中 .isoformat() 返回无时区后缀的上海时间字符串
"""
from datetime import datetime, date, timezone, timedelta

# 上海时区（UTC+8）
SHANGHAI_TZ = timezone(timedelta(hours=8))


def now_shanghai() -> datetime:
    """返回当前上海时间的 naive datetime（无 tzinfo，用于写入数据库）"""
    return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)


def today_shanghai() -> date:
    """返回当前上海日期"""
    return now_shanghai().date()
