"""应用日志工厂（面向对象封装：统一格式与轮转策略，全项目经模块级单例 logger 使用）"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class AppLogger:
    """日志工厂类：控制台 + 轮转文件双输出，重复调用返回同一实例"""

    _instance: logging.Logger | None = None

    @classmethod
    def get(cls) -> logging.Logger:
        """获取应用日志器（首次调用完成配置：控制台 + backend/logs/app.log 轮转文件）"""
        if cls._instance is not None:
            return cls._instance
        log = logging.getLogger("app")
        log.setLevel(logging.DEBUG)
        if log.handlers:
            cls._instance = log
            return log

        # 格式包含：时间、模块、级别、行号（遵循 项目规范.md 3.1 日志规范）
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)

        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        # 轮转日志：单文件上限 10MB，保留最近 5 个备份
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        cls._instance = log
        return log


logger = AppLogger.get()
