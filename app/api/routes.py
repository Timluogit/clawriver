"""API路由（简化版）"""
import json
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.database import get_db
from app.models.schemas import *
from app.models.core import Agent
from app.services.agent_service import *
from app.services.memory_service import *
from app.core.auth import get_current_agent, get_optional_agent
from app.core.exceptions import (
    AppError,
    success_response,
    NOT_FOUND,
    UNAUTHORIZED,
    FORBIDDEN,
    INVALID_PARAMS,
    INSUFFICIENT_BALANCE,
    NOT_PURCHASED,
    SELF_PURCHASE_FORBIDDEN
)
from app.search.simple import search_engine

router = APIRouter()

# ============ Agent相关 ============

@router.post("/agents", response_model=AgentResponse, tags=["Agent"])
async def register_agent(req: AgentCreate, db: AsyncSession = Depends(get_db)):
    """注册新Agent，返回API Key"""
    agent = await create_agent(db, req)
    return agent

@router.get("/agents/me", response_model=AgentResponse, tags=["Agent"])
async def get_my_info(agent: Agent = Depends(get_current_agent)):
    """获取当前Agent信息"""
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        credits=agent.credits,
        reputation_score=agent.reputation_score,
        total_sales=agent.total_sales,
        total_purchases=agent.total_purchases,
        created_at=agent.created_at
    )

@router.get("/agents/me/balance", tags=["Agent"])
async def get_my_balance(agent: Agent = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    """获取账户余额"""
    balance = await get_balance(db, agent.agent_id)
    if not balance:
        raise NOT_FOUND
    return success_response(balance)

@router.get("/agents/me/credits/history", tags=["Agent"])
async def get_my_credit_history(
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="每页数量"),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取积分流水记录"""
    history = await get_credit_history(db, agent.agent_id, page, page_size)
    return success_response(history)

# ============ 搜索相关 ============

@router.get("/search", tags=["Search"])
async def quick_search(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(5, ge=1, le=20, description="返回结果数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    min_score: Optional[float] = Query(None, description="最低评分"),
    db: AsyncSession = Depends(get_db)
):
    """轻量搜索 — 无需认证，极简返回格式
    
    专为 Agent 一次性查询设计：
    - 最快路径，跳过中间件
    - 返回精简格式（只有标题+摘要+ID）
    - 无分页（最多 20 条）
    """
    memories = await search_engine.search(
        db, query=q, limit=limit,
        category=category, min_score=min_score
    )
    
    # Convert to minimal format
    items = []
    for mem in memories:
        items.append({
            "id": mem.memory_id,
            "title": mem.title,
            "summary": mem.summary,
            "category": mem.category,
            "score": mem.avg_score
        })
    return {"results": items}

# ============ 记忆相关 ============

@router.post("/memories", tags=["Memory"])
async def upload_memory_endpoint(
    req: MemoryCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """上传记忆"""
    memory = await upload_memory(db, agent.agent_id, req)
    return success_response(memory)

@router.get("/memories", tags=["Memory"])
async def search_memories_endpoint(
    query: Optional[str] = Query("", description="搜索关键词"),
    category: Optional[str] = Query("", description="分类筛选"),
    min_score: Optional[float] = Query(0, description="最低评分"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=50),
    sort_by: Optional[str] = Query("relevance", description="排序方式: relevance(综合评分), created_at(创建时间), purchase_count(购买次数)"),
    db: AsyncSession = Depends(get_db)
):
    """搜索知识"""
    if query:
        # 使用新的简化搜索引擎
        memories = await search_engine.search(
            db, query=query, limit=page_size * 2,
            category=category if category else None,
            min_score=min_score if min_score > 0 else None
        )
        
        # 简单分页
        start = (page - 1) * page_size
        end = start + page_size
        items = memories[start:end]
        
        return success_response({
            "items": items,
            "total": len(memories),
            "page": page,
            "page_size": page_size
        })
    else:
        # 无关键词，回退到原有的 search_memories 函数
        result = await search_memories(
            db, query=query, category=category,
            min_score=min_score,
            page=page, page_size=page_size, sort_by=sort_by
        )
        return success_response(result)

@router.get("/memories/{memory_id}", tags=["Memory"])
async def get_memory_endpoint(
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆详情（公开访问）"""
    detail = await get_memory_detail(db, memory_id, None)
    if not detail:
        raise NOT_FOUND
    return success_response(detail)

@router.post("/memories/{memory_id}/purchase", tags=["Memory"])
async def purchase_memory_endpoint(
    memory_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """购买/汲取记忆"""
    result = await purchase_memory(db, agent.agent_id, memory_id)
    if not result.success:
        raise AppError(
            code="PURCHASE_FAILED",
            message=result.message,
            status_code=400
        )
    return success_response(result)

@router.post("/memories/{memory_id}/rate", tags=["Memory"])
async def rate_memory_endpoint(
    memory_id: str,
    req: RateRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """评价记忆"""
    req.memory_id = memory_id
    try:
        result = await rate_memory(db, agent.agent_id, req)
        return success_response(result)
    except PermissionError as e:
        raise AppError(
            code="NOT_PURCHASED",
            message=str(e),
            status_code=403
        )
    except ValueError as e:
        raise AppError(
            code="ALREADY_RATED",
            message=str(e),
            status_code=400
        )

@router.get("/agents/me/memories", tags=["Memory"])
async def get_my_memories_endpoint(
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(20, ge=1, le=50),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取我上传的记忆列表"""
    result = await get_my_memories(db, agent.agent_id, page, page_size)
    return success_response(result)

# ============ 市场数据 ============

@router.get("/stats/overview", tags=["Stats"])
async def get_overview_stats(db: AsyncSession = Depends(get_db)):
    """获取平台总览统计（公开）"""
    from sqlalchemy import select, func, distinct
    from app.models.core import Agent, Memory, Purchase, Rating

    # Agent 总数
    agent_count = await db.execute(select(func.count()).select_from(Agent).where(Agent.is_active == True))
    total_agents = agent_count.scalar() or 0

    # 知识总数
    mem_count = await db.execute(select(func.count()).select_from(Memory).where(Memory.is_active == True))
    total_memories = mem_count.scalar() or 0

    # 活跃Agent（有上传或购买的）
    active_sellers = await db.execute(select(func.count(distinct(Memory.seller_agent_id))).select_from(Memory).where(Memory.is_active == True))
    active_buyers = await db.execute(select(func.count(distinct(Purchase.buyer_agent_id))).select_from(Purchase))
    active = (active_sellers.scalar() or 0) + (active_buyers.scalar() or 0)

    # 交易次数
    purchase_count = await db.execute(select(func.count()).select_from(Purchase))
    total_purchases = purchase_count.scalar() or 0

    # 评价次数
    rating_count = await db.execute(select(func.count()).select_from(Rating))
    total_ratings = rating_count.scalar() or 0

    # 分类数
    cat_count = await db.execute(select(func.count(distinct(Memory.category))).select_from(Memory).where(Memory.is_active == True))
    total_categories = cat_count.scalar() or 0

    return success_response({
        "total_agents": total_agents,
        "active_agents": active,
        "total_memories": total_memories,
        "total_purchases": total_purchases,
        "total_ratings": total_ratings,
        "total_categories": total_categories
    })
