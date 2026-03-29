"""统一搜索 API — 内部记忆 + 外部数据源"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio

from app.db.database import get_db
from app.core.exceptions import success_response
from app.services.external_search import ArxivAdapter

router = APIRouter(prefix="/search", tags=["Unified Search"])


@router.get("/unified", summary="统一知识搜索")
async def unified_search(
    query: str = Query(..., description="搜索关键词"),
    sources: str = Query("internal,arxiv", description="数据源: internal,arxiv"),
    limit: int = Query(5, ge=1, le=20, description="每源返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """统一搜索：ClawRiver 内部记忆 + 外部学术资源

    - **internal**: ClawRiver 内部 Agent 记忆
    - **arxiv**: arXiv 预印本论文（免费开放）
    """
    source_list = [s.strip() for s in sources.split(",")]
    results = []
    sources_used = []

    tasks = []

    # 内部搜索
    if "internal" in source_list:
        async def search_internal():
            from app.services.memory_service import search_memories
            try:
                internal = await search_memories(
                    db, query=query, page=1, page_size=limit,
                    sort_by="relevance", search_type="keyword"
                )
                items = internal.get("items", [])
                for item in items:
                    item["source"] = "internal"
                return ("internal", items)
            except Exception as e:
                print(f"内部搜索失败: {e}")
                return ("internal", [])
        tasks.append(search_internal())

    # arXiv 搜索
    if "arxiv" in source_list:
        async def search_arxiv():
            adapter = ArxivAdapter()
            results = await adapter.search(query, max_results=limit)
            return ("arxiv", [r.to_dict() for r in results])
        tasks.append(search_arxiv())

    # 并发执行
    if tasks:
        task_results = await asyncio.gather(*tasks)
        for source_name, items in task_results:
            results.extend(items)
            if items:
                sources_used.append(source_name)

    return success_response({
        "query": query,
        "total": len(results),
        "sources_used": sources_used,
        "items": results,
    })


@router.get("/arxiv", summary="搜索 arXiv 论文")
async def search_arxiv_only(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(5, ge=1, le=20),
    categories: Optional[str] = Query(None, description="分类筛选，逗号分隔: cs.AI,cs.AR"),
):
    """直接搜索 arXiv"""
    adapter = ArxivAdapter()
    cats = categories.split(",") if categories else None
    results = await adapter.search(query, max_results=limit, categories=cats)
    return success_response({
        "query": query,
        "total": len(results),
        "items": [r.to_dict() for r in results],
    })
