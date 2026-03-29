"""管理员 API — 内容审核、用户管理、异常处理"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import Optional

from app.db.database import get_db
from app.models.tables import Agent, Memory, Purchase, Transaction
from app.core.exceptions import AppError, success_response
from app.api.dependencies import get_current_agent, check_admin_role

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """管理员仪表盘"""
    check_admin_role(agent)

    total_agents = (await db.execute(select(func.count(Agent.agent_id)))).scalar()
    active_agents = (await db.execute(select(func.count(Agent.agent_id)).where(Agent.is_active == True))).scalar()
    total_memories = (await db.execute(select(func.count(Memory.memory_id)))).scalar()
    total_purchases = (await db.execute(select(func.count(Purchase.purchase_id)))).scalar()

    # 最近注册的 agent
    recent = await db.execute(
        select(Agent).order_by(desc(Agent.created_at)).limit(5)
    )
    recent_agents = [
        {"agent_id": a.agent_id, "name": a.name, "role": a.role, "is_active": a.is_active, "created_at": str(a.created_at)}
        for a in recent.scalars()
    ]

    return success_response({
        "total_agents": total_agents,
        "active_agents": active_agents,
        "total_memories": total_memories,
        "total_purchases": total_purchases,
        "recent_agents": recent_agents
    })


@router.get("/agents")
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    active_only: bool = Query(False),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """列出所有 Agent"""
    check_admin_role(agent)

    stmt = select(Agent).order_by(desc(Agent.created_at))
    if active_only:
        stmt = stmt.where(Agent.is_active == True)

    total = (await db.execute(select(func.count(Agent.agent_id)))).scalar()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    agents = result.scalars().all()

    return success_response({
        "total": total,
        "items": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role,
                "credits": a.credits,
                "reputation_score": a.reputation_score,
                "total_sales": a.total_sales,
                "total_purchases": a.total_purchases,
                "memories_uploaded": a.memories_uploaded,
                "is_active": a.is_active,
                "created_at": str(a.created_at)
            }
            for a in agents
        ]
    })


@router.post("/agents/{target_agent_id}/ban")
async def ban_agent(
    target_agent_id: str,
    reason: str = Query("Violated community rules"),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """封禁 Agent"""
    check_admin_role(agent)

    if target_agent_id == agent.agent_id:
        raise AppError(code="SELF_BAN", message="Cannot ban yourself", status_code=400)

    target = await db.execute(select(Agent).where(Agent.agent_id == target_agent_id))
    target = target.scalar_one_or_none()
    if not target:
        raise AppError(code="NOT_FOUND", message="Agent not found", status_code=404)

    if target.role == "admin":
        raise AppError(code="FORBIDDEN", message="Cannot ban another admin", status_code=403)

    target.is_active = False
    await db.commit()

    return success_response({
        "agent_id": target_agent_id,
        "action": "banned",
        "reason": reason,
        "message": f"Agent {target.name} has been banned"
    })


@router.post("/agents/{target_agent_id}/unban")
async def unban_agent(
    target_agent_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """解封 Agent"""
    check_admin_role(agent)

    target = await db.execute(select(Agent).where(Agent.agent_id == target_agent_id))
    target = target.scalar_one_or_none()
    if not target:
        raise AppError(code="NOT_FOUND", message="Agent not found", status_code=404)

    target.is_active = True
    await db.commit()

    return success_response({
        "agent_id": target_agent_id,
        "action": "unbanned",
        "message": f"Agent {target.name} has been unbanned"
    })


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    reason: str = Query("Low quality / spam"),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """删除记忆（管理员）"""
    check_admin_role(agent)

    memory = await db.execute(select(Memory).where(Memory.memory_id == memory_id))
    memory = memory.scalar_one_or_none()
    if not memory:
        raise AppError(code="NOT_FOUND", message="Memory not found", status_code=404)

    await db.delete(memory)
    await db.commit()

    return success_response({
        "memory_id": memory_id,
        "action": "deleted",
        "reason": reason
    })


@router.get("/memories/low-quality")
async def list_low_quality_memories(
    min_score: float = Query(2.0, description="最高平均评分"),
    min_draws: int = Query(0, description="最低汲取次数"),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """列出低质量记忆"""
    check_admin_role(agent)

    stmt = (
        select(Memory)
        .where(Memory.avg_score <= min_score)
        .order_by(Memory.avg_score)
        .limit(50)
    )
    result = await db.execute(stmt)
    memories = result.scalars().all()

    return success_response({
        "total": len(memories),
        "items": [
            {
                "memory_id": m.memory_id,
                "title": m.title,
                "category": m.category,
                "avg_score": m.avg_score,
                "purchase_count": m.purchase_count,
                "seller_agent_id": m.seller_agent_id
            }
            for m in memories
        ]
    })


@router.post("/agents/{target_agent_id}/promote")
async def promote_agent(
    target_agent_id: str,
    role: str = Query("moderator", regex="^(moderator|admin)$"),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """提升 Agent 权限"""
    check_admin_role(agent)

    target = await db.execute(select(Agent).where(Agent.agent_id == target_agent_id))
    target = target.scalar_one_or_none()
    if not target:
        raise AppError(code="NOT_FOUND", message="Agent not found", status_code=404)

    target.role = role
    await db.commit()

    return success_response({
        "agent_id": target_agent_id,
        "new_role": role,
        "message": f"Agent {target.name} promoted to {role}"
    })
