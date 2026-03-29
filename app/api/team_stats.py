"""团队统计 API"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from datetime import datetime, timedelta

from app.api.dependencies import get_db, get_current_agent
from app.models.tables import Agent, Team, TeamMember, Memory, Purchase, TeamCreditTransaction
from app.models.schemas import TeamStatsResponse, MemberActivityStats
from app.core.exceptions import AppError


router = APIRouter(prefix="/teams/{team_id}/stats", tags=["team-stats"])


@router.get("/", response_model=TeamStatsResponse)
async def get_team_stats(
    team_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取团队统计数据

    包括：成员数、记忆数、购买统计、积分统计、活跃度
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 获取团队基本信息
    team_result = await db.execute(
        select(Team).where(Team.team_id == team_id, Team.is_active == True)
    )
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 获取团队记忆数量
    team_memories_result = await db.execute(
        select(func.count()).select_from(Memory).where(
            and_(
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    team_memories_count = team_memories_result.scalar() or 0

    # 获取团队购买数量（购买记录中 buyer_agent_id = team_id）
    team_purchases_result = await db.execute(
        select(func.count()).select_from(Purchase).where(
            Purchase.buyer_agent_id == team_id
        )
    )
    total_purchases = team_purchases_result.scalar() or 0

    # 获取团队销售数量（团队创建的记忆被购买次数）
    team_sales_result = await db.execute(
        select(func.sum(Memory.purchase_count)).select_from(Memory).where(
            and_(
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    total_sales = team_sales_result.scalar() or 0

    # 计算7天活跃成员数
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_7d_result = await db.execute(
        select(func.count()).select_from(TeamActivityLog).where(
            and_(
                TeamActivityLog.team_id == team_id,
                TeamActivityLog.created_at >= seven_days_ago
            )
        )
    )
    active_7d_count = active_7d_result.scalar() or 0

    # 计算30天活跃成员数
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_30d_result = await db.execute(
        select(func.count()).select_from(TeamActivityLog).where(
            and_(
                TeamActivityLog.team_id == team_id,
                TeamActivityLog.created_at >= thirty_days_ago
            )
        )
    )
    active_30d_count = active_30d_result.scalar() or 0

    return TeamStatsResponse(
        team_id=team.team_id,
        name=team.name,
        member_count=team.member_count,
        memory_count=team.memory_count,
        team_memories_count=team_memories_count,
        total_purchases=total_purchases,
        total_sales=total_sales,
        credits=team.credits,
        total_earned=team.total_earned,
        total_spent=team.total_spent,
        active_members_7d=active_7d_count,
        active_members_30d=active_30d_count,
        created_at=team.created_at
    )


@router.get("/members", response_model=List[MemberActivityStats])
async def get_member_activity_stats(
    team_id: str,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取成员活跃度统计

    Args:
        team_id: 团队ID
        days: 统计天数
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 计算时间范围
    start_date = datetime.now() - timedelta(days=days)

    # 获取所有团队成员
    members_result = await db.execute(
        select(TeamMember, Agent)
        .join(Agent, TeamMember.agent_id == Agent.agent_id)
        .where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.is_active == True
            )
        )
        .order_by(TeamMember.joined_at)
    )

    stats_list = []

    for row in members_result:
        member = row[0]
        agent = row[1]

        # 统计创建的记忆数
        created_memories_result = await db.execute(
            select(func.count()).select_from(Memory).where(
                and_(
                    Memory.team_id == team_id,
                    Memory.created_by_agent_id == agent.agent_id,
                    Memory.is_active == True,
                    Memory.created_at >= start_date
                )
            )
        )
        memories_created = created_memories_result.scalar() or 0

        # 统计购买的记忆数（个人购买）
        purchased_memories_result = await db.execute(
            select(func.count()).select_from(Purchase).where(
                and_(
                    Purchase.buyer_agent_id == agent.agent_id,
                    Purchase.created_at >= start_date
                )
            )
        )
        memories_purchased = purchased_memories_result.scalar() or 0

        # 统计总购买次数
        purchases_count_result = await db.execute(
            select(func.count()).select_from(Purchase).where(
                and_(
                    Purchase.buyer_agent_id == agent.agent_id,
                    Purchase.created_at >= start_date
                )
            )
        )
        purchases_count = purchases_count_result.scalar() or 0

        # 获取最后活跃时间（从活动日志）
        last_activity_result = await db.execute(
            select(func.max(TeamActivityLog.created_at)).where(
                and_(
                    TeamActivityLog.team_id == team_id,
                    TeamActivityLog.agent_id == agent.agent_id
                )
            )
        )
        last_active_at = last_activity_result.scalar() or member.joined_at

        stats_list.append(MemberActivityStats(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            role=member.role,
            memories_created=memories_created,
            memories_purchased=memories_purchased,
            purchases_count=purchases_count,
            last_active_at=last_active_at
        ))

    return stats_list


@router.get("/credits")
async def get_credits_usage_stats(
    team_id: str,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取团队积分使用统计

    Args:
        team_id: 团队ID
        days: 统计天数
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 计算时间范围
    start_date = datetime.now() - timedelta(days=days)

    # 获取团队当前积分
    team_result = await db.execute(
        select(Team).where(Team.team_id == team_id)
    )
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 统计期间充值金额
    recharge_result = await db.execute(
        select(func.sum(TeamCreditTransaction.amount)).select_from(TeamCreditTransaction).where(
            and_(
                TeamCreditTransaction.team_id == team_id,
                TeamCreditTransaction.tx_type == "recharge",
                TeamCreditTransaction.created_at >= start_date
            )
        )
    )
    total_recharged = recharge_result.scalar() or 0

    # 统计期间购买支出
    purchase_result = await db.execute(
        select(func.sum(TeamCreditTransaction.amount)).select_from(TeamCreditTransaction).where(
            and_(
                TeamCreditTransaction.team_id == team_id,
                TeamCreditTransaction.tx_type == "purchase",
                TeamCreditTransaction.created_at >= start_date
            )
        )
    )
    total_purchased = abs(purchase_result.scalar()) if purchase_result.scalar() else 0

    # 统计期间销售收入
    sale_result = await db.execute(
        select(func.sum(TeamCreditTransaction.amount)).select_from(TeamCreditTransaction).where(
            and_(
                TeamCreditTransaction.team_id == team_id,
                TeamCreditTransaction.tx_type == "sale",
                TeamCreditTransaction.created_at >= start_date
            )
        )
    )
    total_sold = sale_result.scalar() or 0

    # 获取交易记录
    transactions_result = await db.execute(
        select(TeamCreditTransaction, Agent)
        .outerjoin(Agent, TeamCreditTransaction.agent_id == Agent.agent_id)
        .where(
            and_(
                TeamCreditTransaction.team_id == team_id,
                TeamCreditTransaction.created_at >= start_date
            )
        )
        .order_by(desc(TeamCreditTransaction.created_at))
        .limit(50)
    )

    transactions = []
    for row in transactions_result:
        tx = row[0]
        agent = row[1]
        transactions.append({
            "tx_id": tx.tx_id,
            "tx_type": tx.tx_type,
            "amount": tx.amount,
            "balance_after": tx.balance_after,
            "related_id": tx.related_id,
            "description": tx.description,
            "agent_name": agent.name if agent else None,
            "created_at": tx.created_at.isoformat()
        })

    return {
        "current_credits": team.credits,
        "total_recharged": total_recharged,
        "total_purchased": total_purchased,
        "total_sold": total_sold,
        "net_change": total_recharged - total_purchased + total_sold,
        "period_days": days,
        "recent_transactions": transactions
    }


# 导入 TeamActivityLog
from app.models.tables import TeamActivityLog
