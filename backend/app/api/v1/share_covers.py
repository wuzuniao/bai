"""
转发封面临时存储路由（/api/v1/share-covers）
--------------------------------------------------------------------------
- POST ''：上传封面 PNG（鉴权；前端 canvas 导出小图），返回 {path} 相对 URL，
  前端拼接 API 基地址后作为 onShareAppMessage 的 imageUrl
- GET /{name}：读取封面（不鉴权——微信客户端抓取封面时不携带令牌；文件名为内容
  哈希不可枚举，超 TTL 由清理任务删除后 404）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...core.config import settings
from ...core.deps import get_current_user_id
from ...core.response import response_service
from ...services.share_cover_service import share_cover_service as svc

router = APIRouter(prefix="/share-covers", tags=["share-covers"])


@router.post("")
async def upload_share_cover(
    file: UploadFile,
    user_id: int = Depends(get_current_user_id),
) -> dict:
    """上传转发封面 PNG（内容寻址落盘），返回相对路径（前端拼接 API 基地址作 imageUrl）"""
    # 多读 1 字节用于判超上限（read 上界截断时区分恰好等于与超过）
    data = await file.read(svc.MAX_BYTES + 1)
    name = svc.save(data)
    return response_service.ok({"path": f"{settings.API_V1_STR}/share-covers/{name}"})


@router.get("/{name}")
async def get_share_cover(name: str) -> FileResponse:
    """读取转发封面（PNG；一周 TTL，过期由清理任务删除后 404）"""
    path = svc.path_of(name)
    if path is None:
        raise HTTPException(status_code=404, detail="封面不存在或已过期")
    # 封面不可变（内容寻址），允许客户端/微信按周缓存
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800"},
    )
