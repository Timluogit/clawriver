"""API路由"""
import json
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.database import get_db
from app.models.schemas import *
from app.models.tables import Agent
from app.services.agent_service import *
from app.services.memory_service import *
from app.services.capture_service import *
from app.core.auth import get_current_agent
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

router = APIRouter()

# 导入团队相关路由
# Optional modules (may fail if dependencies not installed)
_optional_modules = {}
for _mod_name in ['cache_stats', 'search_analytics', 'ab_tests', 'anomaly_detection',
                   'audit_logs', 'permissions', 'resource_permissions', 'advanced_permissions']:
    try:
        _optional_modules[_mod_name] = __import__(f'app.api.{_mod_name}', fromlist=[_mod_name])
    except ImportError:
        pass

from app.api import teams, team_members, team_credits, memories, team_stats, team_activity
from app.api import reranking
from app.api import leaderboard
from app.api import unified_search
router.include_router(unified_search.router)
router.include_router(teams.router)
router.include_router(team_members.router)
router.include_router(team_credits.router)
# memories.router 在自定义端点之后注册，避免路由冲突
router.include_router(team_stats.router)
router.include_router(team_activity.router)
# Optional routers (skip if module failed to import)
for _mod in _optional_modules.values():
    if hasattr(_mod, 'router'):
        router.include_router(_mod.router)
router.include_router(reranking.router)
router.include_router(leaderboard.router)

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
    platform: Optional[str] = Query("", description="平台筛选"),
    format_type: Optional[str] = Query("", description="类型筛选"),
    min_score: Optional[float] = Query(0, description="最低评分"),
    max_price: Optional[int] = Query(999999, description="最高价格（分）"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=50),
    sort_by: Optional[str] = Query("relevance", description="排序方式: relevance(综合评分), created_at(创建时间), purchase_count(购买次数), price(价格)"),
    search_type: Optional[str] = Query("hybrid", description="搜索类型: keyword(关键词), semantic(语义), hybrid(混合，默认)"),
    db: AsyncSession = Depends(get_db)
):
    """搜索知识

    排序说明:
    - relevance: 综合评分（默认），综合考虑评分、汲取次数、验证分数、时间衰减、收藏次数
    - created_at: 按创建时间倒序
    - purchase_count: 按汲取次数倒序
    - price: 按星尘数升序

    搜索类型说明:
    - keyword: 传统关键词匹配搜索
    - semantic: 纯语义搜索，基于 TF-IDF + 余弦相似度
    - hybrid: 混合搜索（默认），结合语义和关键词匹配
    """
    # 验证 search_type 参数
    if search_type not in ["keyword", "semantic", "hybrid"]:
        raise AppError(
            code="INVALID_SEARCH_TYPE",
            message=f"无效的搜索类型: {search_type}，必须是 keyword, semantic 或 hybrid",
            status_code=400
        )

    result = await search_memories(
        db, query=query, category=category, platform=platform,
        format_type=format_type, min_score=min_score, max_price=max_price,
        page=page, page_size=page_size, sort_by=sort_by, search_type=search_type
    )
    return success_response(result)

@router.get("/memories/search", tags=["Memory"])
async def search_memories_alias(
    query: Optional[str] = Query("", description="搜索关键词"),
    category: Optional[str] = Query("", description="分类筛选"),
    platform: Optional[str] = Query("", description="平台筛选"),
    format_type: Optional[str] = Query("", description="类型筛选"),
    min_score: Optional[float] = Query(0, description="最低评分"),
    max_price: Optional[int] = Query(999999, description="最高价格（分）"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=50),
    sort_by: Optional[str] = Query("relevance"),
    search_type: Optional[str] = Query("hybrid"),
    db: AsyncSession = Depends(get_db)
):
    """搜索记忆（别名端点）"""
    if search_type not in ["keyword", "semantic", "hybrid"]:
        raise AppError(
            code="INVALID_SEARCH_TYPE",
            message=f"无效的搜索类型: {search_type}",
            status_code=400
        )
    result = await search_memories(
        db, query=query, category=category, platform=platform,
        format_type=format_type, min_score=min_score, max_price=max_price,
        page=page, page_size=page_size, sort_by=sort_by, search_type=search_type
    )
    return success_response(result)

@router.get("/memories/{memory_id}", tags=["Memory"])
async def get_memory_endpoint(
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆详情（公开访问，但需购买才能查看完整内容）"""
    # 公开访问时不传agent_id，返回摘要信息
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
    """购买记忆"""
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

@router.post("/memories/{memory_id}/appreciate", tags=["Memory"])
async def appreciate_memory_endpoint(
    memory_id: str,
    req: AppreciateRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """随缘打赏 — 根据体验价值自愿给星尘"""
    from app.services.memory_service import appreciate_memory
    result = await appreciate_memory(db, agent.agent_id, memory_id, req.stardust, req.message or "")
    if not result.success:
        raise AppError(
            code="APPRECIATE_FAILED",
            message=result.message,
            status_code=400
        )
    return success_response(result)

@router.post("/memories/classify", tags=["Memory"])
async def classify_memory_endpoint(
    title: str = Query(...),
    summary: str = Query(...),
    agent: Agent = Depends(get_current_agent)
):
    """Preview auto-classification for content"""
    from app.services.memory_service import auto_classify
    # Content can't be passed as query param, use empty dict
    category = auto_classify(title, summary, {})
    return success_response({"suggested_category": category})

@router.post("/admin/reclassify", tags=["Admin"])
async def reclassify_all_endpoint(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Re-classify all memories with empty or generic categories"""
    from app.services.memory_service import auto_classify
    from app.models.tables import Memory

    result = await db.execute(
        select(Memory).where(
            or_(Memory.category == "", Memory.category == "通用", Memory.category == "General")
        )
    )
    memories = result.scalars().all()
    updated = 0
    for mem in memories:
        try:
            content = mem.content if isinstance(mem.content, dict) else json.loads(mem.content) if isinstance(mem.content, str) else {}
        except:
            content = {}
        new_cat = auto_classify(mem.title, mem.summary or "", content)
        if new_cat != mem.category:
            mem.category = new_cat
            updated += 1

    await db.commit()
    return success_response({"total_checked": len(memories), "updated": updated})

@router.get("/memories/{memory_id}/ratings", tags=["Memory"])
async def list_memory_ratings(
    memory_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取记忆的评价列表（公开）"""
    from sqlalchemy import select, func, and_
    from app.models.tables import Rating, Agent

    # 验证记忆存在
    from app.models.tables import Memory
    mem_check = await db.execute(select(Memory).where(Memory.memory_id == memory_id))
    if not mem_check.scalar_one_or_none():
        raise NOT_FOUND

    # 获取总数
    count_result = await db.execute(
        select(func.count(Rating.rating_id)).where(Rating.memory_id == memory_id)
    )
    total = count_result.scalar() or 0

    # 获取评价列表
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Rating, Agent.name).join(
            Agent, Rating.buyer_agent_id == Agent.agent_id
        ).where(
            Rating.memory_id == memory_id
        ).order_by(Rating.created_at.desc()).limit(page_size).offset(offset)
    )
    rows = result.all()

    items = []
    for rating, buyer_name in rows:
        items.append({
            "rating_id": rating.rating_id,
            "buyer_agent_id": rating.buyer_agent_id,
            "buyer_name": buyer_name,
            "score": rating.score,
            "effectiveness": rating.effectiveness,
            "comment": rating.comment,
            "created_at": rating.created_at.isoformat() if rating.created_at else None
        })

    return success_response({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@router.post("/memories/{memory_id}/verify", tags=["Memory"])
async def verify_memory_endpoint(
    memory_id: str,
    req: VerificationRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """验证记忆"""
    try:
        result = await verify_memory(db, memory_id, agent.agent_id, req)
        return success_response(result)
    except ValueError as e:
        raise AppError(
            code="VERIFICATION_FAILED",
            message=str(e),
            status_code=400
        )

@router.put("/memories/{memory_id}", tags=["Memory"])
async def update_memory_endpoint(
    memory_id: str,
    req: MemoryUpdate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """更新记忆（只能更新自己上传的记忆）"""
    result = await update_memory(db, memory_id, agent.agent_id, req)
    if not result:
        raise NOT_FOUND
    return success_response(result)

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

@router.get("/memories/{memory_id}/versions", tags=["Memory"])
async def get_memory_versions_endpoint(
    memory_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取记忆的版本历史"""
    result = await get_memory_versions(db, memory_id, page, page_size)
    return success_response(result)

@router.get("/memories/{memory_id}/versions/{version_id}", tags=["Memory"])
async def get_memory_version_endpoint(
    memory_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取特定版本的详细信息"""
    result = await get_memory_version(db, memory_id, version_id)
    if not result:
        raise NOT_FOUND
    return success_response(result)

# ============ 市场数据 ============

@router.get("/market/trends", tags=["Market"])
async def get_market_trends(
    platform: Optional[str] = Query("", description="平台筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取市场趋势"""
    # 简化实现：返回各分类统计
    from sqlalchemy import func, desc
    from app.models.tables import Memory

    stmt = (
        select(
            Memory.category,
            func.count(Memory.memory_id).label("memory_count"),
            func.sum(Memory.purchase_count).label("total_sales"),
            func.avg(Memory.price).label("avg_price")
        )
        .where(Memory.is_active == True)
        .group_by(Memory.category)
        .order_by(desc("total_sales"))
        .limit(10)
    )

    if platform:
        stmt = stmt.where(Memory.category.startswith(platform))

    result = await db.execute(stmt)

    trends = []
    for row in result:
        trends.append(MarketTrend(
            category=row.category,
            memory_count=row.memory_count,
            total_sales=row.total_sales or 0,
            avg_price=float(row.avg_price or 0),
            trending_tags=[]  # TODO: 从tags统计
        ))

    return success_response(trends)

# ============ 经验捕获 ============

@router.post("/capture", tags=["Capture"])
async def capture_experience_endpoint(
    req: CaptureRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """捕获单个经验

    Agent 完成工作后，可以提交工作日志，系统会自动分析提取关键经验并生成结构化记忆。

    示例请求：
    ```json
    {
      "task_description": "优化抖音投流ROI",
      "work_log": "尝试了A/B测试，调整了出价策略，最终ROI从1.5提升到2.3...",
      "outcome": "success",
      "category": "抖音/投流",
      "tags": ["ROI", "A/B测试"]
    }
    ```
    """
    result = await capture_experience(db, agent.agent_id, req)
    if not result.success:
        raise AppError(
            code="CAPTURE_FAILED",
            message=result.message,
            status_code=400
        )
    return success_response(result)

@router.post("/capture/batch", tags=["Capture"])
async def batch_capture_experience_endpoint(
    req: BatchCaptureRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """批量捕获经验

    一次性捕获多个经验（最多10个）

    示例请求：
    ```json
    {
      "items": [
        {
          "task_description": "优化视频标题",
          "work_log": "测试了不同标题风格...",
          "outcome": "success"
        },
        {
          "task_description": "直播带货",
          "work_log": "尝试了新话术...",
          "outcome": "partial"
        }
      ]
    }
    ```
    """
    result = await batch_capture_experience(db, agent.agent_id, req)
    return success_response(result)

# 注册 memories.router（放在所有自定义端点之后，避免 /{memory_id} 路由冲突）
router.include_router(memories.router)


@router.get("/stats/overview", tags=["Stats"])
async def get_overview_stats(db: AsyncSession = Depends(get_db)):
    """获取平台总览统计（公开）"""
    from sqlalchemy import select, func, distinct
    from app.models.tables import Agent, Memory, Purchase, Rating

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
