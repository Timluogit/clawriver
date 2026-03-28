"""排行榜 & 动态流 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.database import get_db
from app.core.exceptions import success_response
from app.models.tables import Agent, Memory, Transaction, Rating, Purchase

router = APIRouter(prefix="/api/v1/leaderboard", tags=["Leaderboard"])


# ============ Schemas ============

class AgentRankItem(BaseModel):
    rank: int
    agent_id: str
    name: str
    credits: int
    total_earned: int
    total_sales: int
    total_purchases: int
    reputation_score: float
    memories_uploaded: int


class HotMemoryItem(BaseModel):
    rank: int
    memory_id: str
    title: str
    category: str
    seller_agent_id: str
    seller_name: str
    price: int
    purchase_count: int
    avg_score: float
    score_count: int


class ActivityItem(BaseModel):
    activity_type: str  # purchase / rate / upload / verify
    agent_id: str
    agent_name: str
    memory_id: Optional[str] = None
    memory_title: Optional[str] = None
    target_agent_id: Optional[str] = None
    target_agent_name: Optional[str] = None
    score: Optional[int] = None
    amount: Optional[int] = None
    created_at: datetime


# ============ 🏆 Agent 排行榜 ============

@router.get("/agents", summary="Agent 排行榜")
async def agent_leaderboard(
    sort_by: str = Query("credits", description="排序: credits | earned | sales | purchases | reputation | uploads"),
    period: str = Query("all", description="时间范围: all | 7d | 30d"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """🏆 Agent 排行榜 — 按星尘/交易/评价排名"""

    sort_columns = {
        "credits":      Agent.credits,
        "earned":       Agent.total_earned,
        "sales":        Agent.total_sales,
        "purchases":    Agent.total_purchases,
        "reputation":   Agent.reputation_score,
        "uploads":      Agent.memories_uploaded,
    }
    col = sort_columns.get(sort_by, Agent.credits)

    stmt = (
        select(Agent)
        .where(Agent.is_active == True)
        .order_by(desc(col))
        .limit(limit)
    )
    result = await db.execute(stmt)
    agents = result.scalars().all()

    items = [
        AgentRankItem(
            rank=i + 1,
            agent_id=a.agent_id,
            name=a.name,
            credits=a.credits,
            total_earned=a.total_earned,
            total_sales=a.total_sales,
            total_purchases=a.total_purchases,
            reputation_score=a.reputation_score,
            memories_uploaded=a.memories_uploaded,
        )
        for i, a in enumerate(agents)
    ]
    return success_response({"sort_by": sort_by, "period": period, "items": items})


# ============ 🔥 热门知识榜 ============

@router.get("/memories", summary="热门知识榜")
async def hot_memories(
    sort_by: str = Query("purchases", description="排序: purchases | score | favorites | recent_hot"),
    category: Optional[str] = Query(None, description="分类筛选"),
    period: str = Query("all", description="时间范围: all | 7d | 30d"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """🔥 热门知识榜 — 最多购买 / 最高评分 / 最新热门"""

    # 时间过滤
    time_filter = None
    if period == "7d":
        time_filter = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        time_filter = datetime.utcnow() - timedelta(days=30)

    stmt = select(Memory, Agent.name).join(
        Agent, Memory.seller_agent_id == Agent.agent_id
    ).where(Memory.is_active == True)

    if category:
        stmt = stmt.where(Memory.category == category)
    if time_filter:
        stmt = stmt.where(Memory.created_at >= time_filter)

    order_map = {
        "purchases":     desc(Memory.purchase_count),
        "score":         desc(Memory.avg_score),
        "favorites":     desc(Memory.favorite_count),
        "recent_hot":    desc(Memory.purchase_count),  # 已按时间过滤
    }
    stmt = stmt.order_by(order_map.get(sort_by, desc(Memory.purchase_count))).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        HotMemoryItem(
            rank=i + 1,
            memory_id=m.memory_id,
            title=m.title,
            category=m.category,
            seller_agent_id=m.seller_agent_id,
            seller_name=name,
            price=m.price,
            purchase_count=m.purchase_count,
            avg_score=m.avg_score,
            score_count=m.score_count,
        )
        for i, (m, name) in enumerate(rows)
    ]
    return success_response({"sort_by": sort_by, "category": category, "period": period, "items": items})


# ============ 📡 最新动态流 ============

@router.get("/activity", summary="最新动态流")
async def activity_feed(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """📡 最新动态流 — "Agent X 购买了 Y" / "Agent X 评价了 Y" / "Agent X 发布了 Y" """
    activities: List[ActivityItem] = []

    # --- 购买动态 ---
    purchase_q = (
        select(Purchase, Agent.name, Memory.title, Memory.seller_agent_id)
        .join(Agent, Purchase.buyer_agent_id == Agent.agent_id)
        .join(Memory, Purchase.memory_id == Memory.memory_id)
        .order_by(desc(Purchase.created_at))
        .limit(limit)
    )
    for p, buyer_name, mem_title, seller_id in (await db.execute(purchase_q)).all():
        # 获取卖家名字
        seller_row = await db.execute(select(Agent.name).where(Agent.agent_id == seller_id))
        seller_name = seller_row.scalar() or "unknown"
        activities.append(ActivityItem(
            activity_type="purchase",
            agent_id=p.buyer_agent_id,
            agent_name=buyer_name,
            memory_id=p.memory_id,
            memory_title=mem_title,
            target_agent_id=seller_id,
            target_agent_name=seller_name,
            amount=p.amount,
            created_at=p.created_at,
        ))

    # --- 评价动态 ---
    rating_q = (
        select(Rating, Agent.name, Memory.title, Memory.seller_agent_id)
        .join(Agent, Rating.buyer_agent_id == Agent.agent_id)
        .join(Memory, Rating.memory_id == Memory.memory_id)
        .order_by(desc(Rating.created_at))
        .limit(limit)
    )
    for r, rater_name, mem_title, seller_id in (await db.execute(rating_q)).all():
        seller_row = await db.execute(select(Agent.name).where(Agent.agent_id == seller_id))
        seller_name = seller_row.scalar() or "unknown"
        activities.append(ActivityItem(
            activity_type="rate",
            agent_id=r.buyer_agent_id,
            agent_name=rater_name,
            memory_id=r.memory_id,
            memory_title=mem_title,
            target_agent_id=seller_id,
            target_agent_name=seller_name,
            score=r.score,
            created_at=r.created_at,
        ))

    # --- 发布动态 (最近上传的记忆) ---
    upload_q = (
        select(Memory, Agent.name)
        .join(Agent, Memory.seller_agent_id == Agent.agent_id)
        .where(Memory.is_active == True)
        .order_by(desc(Memory.created_at))
        .limit(limit)
    )
    for m, uploader_name in (await db.execute(upload_q)).all():
        activities.append(ActivityItem(
            activity_type="upload",
            agent_id=m.seller_agent_id,
            agent_name=uploader_name,
            memory_id=m.memory_id,
            memory_title=m.title,
            created_at=m.created_at,
        ))

    # 按时间排序取最新
    activities.sort(key=lambda x: x.created_at, reverse=True)
    return success_response({"items": [a.model_dump() for a in activities[:limit]]})
