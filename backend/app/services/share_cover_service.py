"""
转发封面临时存储服务
--------------------------------------------------------------------------
微信真机不接受本地临时文件路径作为转发封面 imageUrl（开发者工具正常），划词
分享卡片封面须经服务端 URL 提供：前端 canvas 导出 PNG 后上传（POST /api/v1/
share-covers），落临时目录后经 GET /api/v1/share-covers/<name> 读取。

- 文件名内容寻址（sha256 前 32 位十六进制）：同一封面重复上传复用同文件，天然去重
- 读取不鉴权（微信客户端抓取封面不带令牌），文件名为内容哈希不可枚举
- 目录按 TTL 轮询清理（默认 7 天，main.py lifespan 拉起后台循环每日一轮）
- 不落库；容器内为临时存储，重新部署即清空（已发出的转发卡片已被微信抓取缓存）
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from ..core.config import settings
from ..core.exceptions import BusinessError


class ShareCoverService:
    """转发封面 PNG 的落盘存取与过期清理（模块级单例 share_cover_service 对外暴露）"""

    # 合法文件名（内容哈希 + 固定扩展；GET 路由据此拦截路径穿越等非法名）
    NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.png$")
    # PNG 魔数（内容校验，拒收非图片载荷）
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    # 单文件上限：5:4 小图富余充足，同时封顶防滥用
    MAX_BYTES = 2 * 1024 * 1024

    def __init__(self) -> None:
        self._dir = Path(settings.SHARE_COVER_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes) -> str:
        """
        校验并保存封面 PNG，返回文件名
        :param data: 上传的完整字节
        :return: 文件名（sha256 前 32 位十六进制 + .png）
        :raises BusinessError: 空内容 / 超大小上限 / 非 PNG 魔数
        """
        if len(data) == 0 or len(data) > self.MAX_BYTES:
            raise BusinessError("封面图片大小超出限制")
        if not data.startswith(self.PNG_MAGIC):
            raise BusinessError("封面格式不正确")
        name = hashlib.sha256(data).hexdigest()[:32] + ".png"
        (self._dir / name).write_bytes(data)
        return name

    def path_of(self, name: str) -> Path | None:
        """
        文件名校验并返回磁盘路径
        :param name: 请求路径中的文件名
        :return: 存在则返回绝对路径，非法或不存在返回 None（路由层转 404）
        """
        if not self.NAME_PATTERN.match(name):
            return None
        path = self._dir / name
        return path if path.is_file() else None

    def cleanup_expired(self) -> int:
        """删除超过 TTL 的封面文件（后台循环每日调用），返回删除数"""
        cutoff = time.time() - settings.SHARE_COVER_TTL_DAYS * 86400
        removed = 0
        for path in self._dir.iterdir():
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        return removed


share_cover_service = ShareCoverService()
