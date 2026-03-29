"""统一搜索 API — 内部记忆 + 外部数据源"""
from fastapi import APIRouter, Query, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio
from collections import defaultdict
from time import time

from app.db.database import get_db
from app.core.exceptions import success_response, AppError
from app.services.external_search import ArxivAdapter, OpenAlexAdapter, HackerNewsAdapter, SemanticScholarAdapter

router = APIRouter(prefix="/search", tags=["Unified Search"])

# Rate limit storage: {ip: [(timestamp, count)]}
rate_limit_storage = defaultdict(list)
RATE_LIMIT_MAX = 10  # Max requests
RATE_LIMIT_WINDOW = 60  # Window in seconds (1 minute)


def check_rate_limit(request: Request):
    """Simple in-memory rate limiting per IP"""
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    
    # Clean up old entries
    rate_limit_storage[client_ip] = [
        (ts, cnt) for ts, cnt in rate_limit_storage[client_ip]
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    # Calculate current count
    current_count = sum(cnt for _, cnt in rate_limit_storage[client_ip])
    
    if current_count >= RATE_LIMIT_MAX:
        raise AppError(
            status_code=429,
            code="rate_limit_exceeded",
            message="Too many requests. Please try again later."
        )
    
    # Add new request
    rate_limit_storage[client_ip].append((now, 1))


@router.get("/unified", summary="统一知识搜索")
async def unified_search(
    query: str = Query(..., description="搜索关键词"),
    sources: str = Query("internal,openalex,hackernews", description="数据源: internal,arxiv,openalex,hackernews,semantic_scholar"),
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

    # OpenAlex 搜索（全学科论文）
    if "openalex" in source_list:
        async def search_openalex():
            try:
                adapter = OpenAlexAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("openalex", [r.to_dict() for r in results])
            except Exception:
                return ("openalex", [])
        tasks.append(search_openalex())

    # Hacker News 搜索（技术文章）
    if "hackernews" in source_list:
        async def search_hackernews():
            try:
                adapter = HackerNewsAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("hackernews", [r.to_dict() for r in results])
            except Exception:
                return ("hackernews", [])
        tasks.append(search_hackernews())

    # Semantic Scholar 搜索（学术论文+引用）
    if "semantic_scholar" in source_list or "semantic" in source_list:
        async def search_s2():
            try:
                adapter = SemanticScholarAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("semantic_scholar", [r.to_dict() for r in results])
            except Exception:
                return ("semantic_scholar", [])
        tasks.append(search_s2())

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


@router.get("/public", summary="公开搜索接口（无需API Key）")
async def public_search(
    request: Request,
    query: str = Query(..., description="搜索关键词"),
    sources: str = Query("openalex,hackernews", description="数据源: openalex,hackernews,arxiv,semantic_scholar"),
    limit: int = Query(5, ge=1, le=20, description="每源返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """公开搜索接口：无需 API Key，用于前端使用，包含 Rate Limit

    - **openalex**: OpenAlex 论文
    - **hackernews**: Hacker News 文章
    - **arxiv**: arXiv 预印本
    - **semantic_scholar**: Semantic Scholar
    """
    # Check rate limit
    check_rate_limit(request)
    
    # Call the internal unified search without 'internal' source
    source_list = [s.strip() for s in sources.split(",")]
    # Remove 'internal' source from public search
    source_list = [s for s in source_list if s != "internal"]
    
    results = []
    sources_used = []

    tasks = []

    # arXiv 搜索
    if "arxiv" in source_list:
        async def search_arxiv():
            adapter = ArxivAdapter()
            results = await adapter.search(query, max_results=limit)
            return ("arxiv", [r.to_dict() for r in results])
        tasks.append(search_arxiv())

    # OpenAlex 搜索（全学科论文）
    if "openalex" in source_list:
        async def search_openalex():
            try:
                adapter = OpenAlexAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("openalex", [r.to_dict() for r in results])
            except Exception:
                return ("openalex", [])
        tasks.append(search_openalex())

    # Hacker News 搜索（技术文章）
    if "hackernews" in source_list:
        async def search_hackernews():
            try:
                adapter = HackerNewsAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("hackernews", [r.to_dict() for r in results])
            except Exception:
                return ("hackernews", [])
        tasks.append(search_hackernews())

    # Semantic Scholar 搜索（学术论文+引用）
    if "semantic_scholar" in source_list or "semantic" in source_list:
        async def search_s2():
            try:
                adapter = SemanticScholarAdapter()
                results = await adapter.search(query, max_results=limit)
                return ("semantic_scholar", [r.to_dict() for r in results])
            except Exception:
                return ("semantic_scholar", [])
        tasks.append(search_s2())

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
