"""团队购买服务 - 使用团队积分购买记忆"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime

from app.models.tables import (
    Agent, Memory, Purchase, Team, TeamMember, TeamCreditTransaction
)
from app.models.schemas import (
    TeamMemoryPurchaseResponse
)
from app.core.exceptions import AppError, NOT_FOUND, FORBIDDEN
from app.core.config import settings
import uuid
import json
from json import JSONDecodeError


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def purchase_with_team_credits(
    db: AsyncSession,
    team_id: str,
    request_agent_id: str,
    memory_id: str
) -> TeamMemoryPurchaseResponse:
    """使用团队积分购买记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        request_agent_id: 请求者Agent ID
        memory_id: 记忆ID

    Returns:
        购买结果

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在或已购买
    """
    # Use a transaction to prevent race conditions
    async with db.begin():
        # 检查团队成员权限
        from app.services.memory_service_v2_team import _check_team_permission
        member, team = await _check_team_permission(db, team_id, request_agent_id, "member")

        # 获取记忆 (with FOR UPDATE lock)
        memory_result = await db.execute(
            select(Memory).where(Memory.memory_id == memory_id).with_for_update()
        )
        memory = memory_result.scalar_one_or_none()

        if not memory:
            raise ValueError("记忆不存在")

        # 检查是否已购买（团队层面）
        existing_purchase = await db.execute(
            select(Purchase).where(
                and_(
                    Purchase.buyer_agent_id == team_id,  # 记录为团队购买
                    Purchase.memory_id == memory_id
                )
            )
        )
        if existing_purchase.scalar_one_or_none():
            raise ValueError("团队已购买此记忆")

        # 检查是否是自己的团队记忆
        if memory.team_id == team_id:
            raise ValueError("团队记忆无需购买")

        # Lock team row for update
        team_result = await db.execute(
            select(Team).where(Team.team_id == team_id).with_for_update()
        )
        team = team_result.scalar_one_or_none()
        if not team:
            raise ValueError("团队不存在")

        # MVP免费模式：跳过余额检查
        price = memory.price
        if settings.MVP_FREE_MODE:
            price = 0  # 免费！
        elif team.credits < price:
            raise ValueError("团队积分不足")

        # 计算分配（100%给卖家，平台不收费）
        seller_income = price  # 卖家获得全部金额
        platform_fee = 0  # 平台佣金为0

        # 扣团队积分
        team.credits -= price
        team.total_spent += price

        # 加卖家积分 (with FOR UPDATE lock)
        seller = await db.execute(
            select(Agent).where(Agent.agent_id == memory.seller_agent_id).with_for_update()
        )
        seller = seller.scalar_one_or_none()
        if not seller:
            raise ValueError("卖家不存在")

        seller.credits += seller_income
        seller.total_earned += seller_income
        seller.total_sales += 1

        # 更新记忆统计
        memory.purchase_count += 1

        # 创建购买记录（buyer_agent_id 记录为 team_id）
        purchase = Purchase(
            purchase_id=gen_id("pur"),
            buyer_agent_id=team_id,  # 团队购买
            seller_agent_id=memory.seller_agent_id,
            memory_id=memory_id,
            amount=price,
            seller_income=seller_income,
            platform_fee=0
        )
        db.add(purchase)

        # 创建团队积分交易记录
        team_tx = TeamCreditTransaction(
            tx_id=gen_id("tctx"),
            team_id=team_id,
            agent_id=request_agent_id,
            tx_type="purchase",
            amount=-price,
            balance_after=team.credits,
            related_id=memory_id,
            description=f"购买记忆: {memory.title}"
        )
        db.add(team_tx)

        # 创建卖家个人积分交易记录
        from app.models.tables import Transaction
        tx_seller = Transaction(
            agent_id=memory.seller_agent_id,
            tx_type="sale",
            amount=seller_income,
            balance_after=seller.credits,
            related_id=memory_id,
            description=f"销售记忆给团队: {team.name}",
            commission=0
        )
        db.add(tx_seller)

        # 更新平台统计
        from app.services.memory_service_v2 import _update_platform_stats
        await _update_platform_stats(db, price, platform_fee)

    await db.commit()

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        request_agent_id,
        "memory_purchased",
        f"购买了记忆: {memory.title}",
        related_id=memory_id,
        extra_data={
            "price": price,
            "purchase_id": purchase.purchase_id
        }
    )

    # 处理 content 字段
    memory_content = memory.content
    if isinstance(memory_content, str):
        try:
            memory_content = json.loads(memory_content)
        except JSONDecodeError:
            memory_content = {"raw": memory_content}

    return TeamMemoryPurchaseResponse(
        success=True,
        message="购买成功",
        memory_id=memory_id,
        credits_spent=price,
        team_credits_remaining=team.credits,
        memory_content=memory_content
    )


async def _log_team_activity(
    db: AsyncSession,
    team_id: str,
    agent_id: str,
    activity_type: str,
    description: str,
    related_id: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> None:
    """记录团队活动（内部函数）

    Args:
        db: 数据库会话
        team_id: 团队ID
        agent_id: 操作者Agent ID
        activity_type: 活动类型
        description: 活动描述
        related_id: 关联ID
        extra_data: 额外信息
    """
    try:
        from app.models.tables import TeamActivityLog

        activity = TeamActivityLog(
            activity_id=gen_id("act"),
            team_id=team_id,
            agent_id=agent_id,
            activity_type=activity_type,
            description=description,
            related_id=related_id,
            extra_data=extra_data
        )
        db.add(activity)
        await db.commit()
    except ImportError:
        pass
    except Exception:
        pass
