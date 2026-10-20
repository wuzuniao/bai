"""
书籍元数据路由（/api/v1/books）
--------------------------------------------------------------------------
- 全部接口需登录（JWT 本地验签），按当前用户隔离数据
- 书籍正文不落库：后端仅存元数据与阅读进度，正文文件由前端沙盒持有
- 响应统一经 core/response.py 的 response_service 包装 {code, msg, data}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.deps import get_current_user_id
from ...core.response import response_service
from ...schemas.reading import (
    BookCreate,
    BookmarksReplace,
    BookOrderBatch,
    BookProgressUpdate,
    ThoughtCreate,
    UnderlineUpsert,
)
from ...services.reading_service import reading_service as svc

router = APIRouter(prefix="/books", tags=["books"])


def _404() -> HTTPException:
    return HTTPException(status_code=404, detail="书籍不存在")


@router.get("")
async def list_books(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """书架列表（按手动排序返回；今日/累计时长经 /reading/stats 查询）"""
    books = await svc.list_books(db, user_id)
    return response_service.ok({"list": [svc.book_to_dict(b) for b in books]})


@router.post("")
async def create_book(
    data: BookCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """导入登记：同用户同名书复用已有行（跨设备按书名关联），否则新建"""
    book, created = await svc.register_book(db, user_id, data)
    return response_service.ok({"created": created, **svc.book_to_dict(book)})


@router.put("/order")
async def update_order(
    data: BookOrderBatch,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """书架手动排序批量更新（拖拽落定一次提交）"""
    updated = await svc.update_order(db, user_id, data)
    return response_service.ok({"updated": updated})


@router.get("/{book_id}")
async def get_book(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """单本书籍详情（含完整阅读进度）"""
    book = await svc.get_book(db, user_id, book_id)
    if book is None:
        raise _404()
    return response_service.ok(svc.book_to_dict(book))


@router.put("/{book_id}")
async def update_book(
    book_id: int,
    data: BookProgressUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """阅读进度回写（任一进度字段出现即刷新最近阅读时刻）"""
    book = await svc.update_book(db, user_id, book_id, data)
    if book is None:
        raise _404()
    return response_service.ok(svc.book_to_dict(book))


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """删除书籍（划线/想法/书签应用层级联清理）"""
    deleted = await svc.delete_book(db, user_id, book_id)
    if not deleted:
        raise _404()
    return response_service.ok()


@router.get("/{book_id}/notes")
async def list_notes(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """书籍的划线与想法列表"""
    data = await svc.list_notes(db, user_id, book_id)
    if data is None:
        raise _404()
    return response_service.ok(data)


@router.put("/{book_id}/notes/underline")
async def upsert_underline(
    book_id: int,
    data: UnderlineUpsert,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """划线按「章+段」upsert（ranges 空数组=整段划线取消）"""
    result = await svc.upsert_underline(db, user_id, book_id, data)
    if result is None:
        raise _404()
    return response_service.ok(result)


@router.post("/{book_id}/notes/thought")
async def create_thought(
    book_id: int,
    data: ThoughtCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """写入想法（跨章选区 + 划线文本快照）"""
    result = await svc.create_thought(db, user_id, book_id, data)
    if result is None:
        raise _404()
    return response_service.ok(result)


@router.get("/{book_id}/bookmarks")
async def list_bookmarks(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """书籍书签列表"""
    data = await svc.list_bookmarks(db, user_id, book_id)
    if data is None:
        raise _404()
    return response_service.ok({"list": data})


@router.put("/{book_id}/bookmarks")
async def replace_bookmarks(
    book_id: int,
    data: BookmarksReplace,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """书签整表替换（前端本地列表即真源快照）"""
    saved = await svc.replace_bookmarks(db, user_id, book_id, data)
    if not saved:
        raise _404()
    return response_service.ok()
