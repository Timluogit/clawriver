"""技术文档检索 API"""
from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Optional
from app.services.doc_search_service import search_docs, get_doc_sources
from app.services.agent_service import get_agent_by_api_key
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/docs", tags=["Doc Search"])

DOC_SEARCH_COST = 5  # 每次搜索消耗 5 星尘


@router.get("/search")
async def doc_search(
    query: str,
    source: Optional[str] = None,
    limit: int = 5,
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索技术文档

    - **query**: 搜索关键词（如 "async await", "docker compose"）
    - **source**: 文档源（python/mdn/fastapi/docker/linux/pypi/npm/github）
    - **limit**: 返回数量，默认 5
    - **X-API-Key**: API Key（必需，每次搜索扣 5 星尘）
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # 验证 Agent
    agent = await get_agent_by_api_key(db, x_api_key)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 检查星尘
    if agent.credits < DOC_SEARCH_COST:
        raise HTTPException(
            status_code=402,
            detail=f"星尘不足。当前: {agent.credits}, 需要: {DOC_SEARCH_COST}"
        )

    # 扣除星尘
    agent.credits -= DOC_SEARCH_COST
    agent.total_spent += DOC_SEARCH_COST
    await db.commit()

    # 搜索文档
    result = await search_docs(query, source, limit)
    result["credits_spent"] = DOC_SEARCH_COST
    result["remaining_credits"] = agent.credits

    return result


@router.get("/sources")
async def doc_sources():
    """获取所有可用的文档源列表（免费）"""
    return {
        "success": True,
        "sources": get_doc_sources(),
        "cost_per_search": DOC_SEARCH_COST,
        "usage": "GET /api/v1/docs/search?query=关键词&source=python"
    }
