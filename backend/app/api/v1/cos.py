"""
书籍文件云端同步路由（/api/v1/cos，腾讯云 COS 对象存储）
--------------------------------------------------------------------------
- 全部接口需登录 + 黑铁及以上会员（令牌 roles 本地比对，非会员 403）
- 用户目录 = auth 用户名（服务间解析，前端不可传入伪造目录）
- 后端经 STS GetFederationToken 换取按用户目录隔离的临时密钥后签发预签名 URL，
  前端持 URL 直传/直取 COS，文件字节不经本服务中转
- 响应统一经 core/response.py 的 response_service 包装 {code, msg, data}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.deps import get_current_payload
from ...core.response import response_service
from ...schemas.cos import CloudBookRequest
from ...services.cos_service import cos_service as svc

router = APIRouter(prefix="/cos", tags=["cos"])


def _member_guard(payload: dict) -> int:
    """会员守卫：返回当前用户 id，非黑铁及以上会员抛 403"""
    if not svc.is_member(payload):
        raise HTTPException(status_code=403, detail="云端同步为黑铁及以上会员专享功能")
    return int(payload["sub"])


@router.get("/objects")
async def list_cloud_objects(payload: dict = Depends(get_current_payload)) -> dict:
    """云端书籍清单（用户目录内全部书籍对象；下载入口据此展示）"""
    user_id = _member_guard(payload)
    user_dir = await svc.get_user_dir(user_id)
    items = await svc.list_objects(user_dir)
    return response_service.ok({"prefix": user_dir, "items": items})


@router.post("/upload-url")
async def create_upload_url(
    data: CloudBookRequest,
    payload: dict = Depends(get_current_payload),
) -> dict:
    """签发单本上传预签名 URL（PUT 对象，10 分钟有效）"""
    user_id = _member_guard(payload)
    user_dir = await svc.get_user_dir(user_id)
    key, url = await svc.create_presigned_put(user_dir, data.title, data.format)
    return response_service.ok({"key": key, "url": url, "expires_in": svc.PRESIGN_TTL})


@router.get("/download-url")
async def create_download_url(
    book_format: str = Query(..., alias="format", max_length=10),
    title: str = Query(..., max_length=200),
    payload: dict = Depends(get_current_payload),
) -> dict:
    """签发单本下载预签名 URL（GET 对象，10 分钟有效）"""
    user_id = _member_guard(payload)
    # 查询参数白名单校验（复用 schema 清洗规则，保证与上传同构）
    data = CloudBookRequest(title=title, format=book_format)
    user_dir = await svc.get_user_dir(user_id)
    key, url = await svc.create_presigned_get(user_dir, data.title, data.format)
    return response_service.ok({"key": key, "url": url, "expires_in": svc.PRESIGN_TTL})


@router.post("/delete")
async def delete_cloud_object(
    data: CloudBookRequest,
    payload: dict = Depends(get_current_payload),
) -> dict:
    """
    删除云端书籍对象（幂等：对象不存在亦成功）
    与其余对象存储接口同口径：黑铁及以上会员方可操作；
    书架删除勾选「同时删除云端数据」时随业务库删除一并触发，同步移除清单条目
    """
    user_id = _member_guard(payload)
    user_dir = await svc.get_user_dir(user_id)
    await svc.delete_cloud_book(user_dir, data.title, data.format)
    return response_service.ok()
