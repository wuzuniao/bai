"""
活动奖励 Pydantic 校验模型（校验逻辑集中本层，路由不散写）
--------------------------------------------------------------------------
- 字段命名与接口 JSON 保持 snake_case（与既有接口风格一致）
- 必填项缺失/越界由 Pydantic 抛 422，业务规则错误由服务层抛 ValueError 转 400
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReadingClaimRequest(BaseModel):
    """阅读档位奖励领取（POST /activity/reading-claim）"""

    tier_minutes: int = Field(gt=0, le=1440, description="档位阈值分钟数")
