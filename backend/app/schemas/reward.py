"""
活动奖励 Pydantic 校验模型（校验逻辑集中本层，路由不散写）
--------------------------------------------------------------------------
- 字段命名与接口 JSON 保持 snake_case（与既有接口风格一致）
- 必填项缺失/越界由 Pydantic 抛 422，业务规则错误由服务层抛 ValueError 转 400
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field


class ReadingClaimRequest(BaseModel):
    """阅读档位奖励领取（POST /activity/reading-claim）"""

    tier_minutes: int = Field(gt=0, le=1440, description="档位阈值分钟数")


class MakeupRequest(BaseModel):
    """会员补签（POST /activity/makeup；日期由 Pydantic 实体解析为 date，路由不再散写解析）"""

    # 字段名与前端请求体保持一致（date: "YYYY-MM-DD" → date 对象）；
    # Annotated 写法规避字段名与类型名同名的 Pydantic 冲突
    date: Annotated[date, Field(description="被补签到日期（YYYY-MM-DD，东八区）")]
