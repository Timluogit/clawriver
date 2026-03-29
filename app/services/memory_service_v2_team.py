"""团队记忆服务层"""
from typing import Optional, List, Literal, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_, desc
from sqlalchemy.orm import selectinload
import uuid

from app.models.tables import Agent, Memory, Team, TeamMember, Purchase, Rating, MemoryVersion
from app.models.schemas import (
    TeamMemoryCreate, TeamMemoryUpdate, TeamMemoryResponse,
    TeamMemoryDetail, TeamMemoryList
)
from app.core.exceptions import AppError, NOT_FOUND, FORBIDDEN
from app.core.config import settings
import json
from json import JSONDecodeError


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _calc_verification_score(data: dict) -> float:
    """计算验证分数（0-1）"""
    score = 0.0
    if data.get("sample_size"):
        score += min(data["sample_size"] / 1000, 0.3)
    if data.get("success_rate"):
        score += data["success_rate"] * 0.3
    if data.get("data_source"):
        score += 0.2
    if data.get("test_period_days"):
        score += min(data["test_period_days"] / 30, 0.2)
    return round(min(score, 1.0), 2)


async def _check_team_permission(
    db: AsyncSession,
    team_id: str,
    agent_id: str,
    min_role: str = "member"
) -> Tuple[TeamMember, Team]:
    """检查团队成员权限

    Args:
        db: 数据库会话
        team_id: 团队ID
        agent_id: Agent ID
        min_role: 最低角色要求（member/admin/owner）

    Returns:
        (成员对象, 团队对象)

    Raises:
        PermissionError: 无权限
        ValueError: 团队不存在
    """
    # 获取团队成员
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.agent_id == agent_id,
                TeamMember.is_active == True
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise PermissionError("不是团队成员")

    # 检查角色
    role_hierarchy = {"member": 0, "admin": 1, "owner": 2}
    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(min_role, 0):
        raise PermissionError(f"需要 {min_role} 或更高权限")

    # 获取团队
    team_result = await db.execute(
        select(Team).where(Team.team_id == team_id, Team.is_active == True)
    )
    team = team_result.scalar_one_or_none()

    if not team:
        raise ValueError("团队不存在")

    return member, team


async def create_team_memory(
    db: AsyncSession,
    team_id: str,
    creator_agent_id: str,
    req: TeamMemoryCreate
) -> TeamMemoryResponse:
    """创建团队共享记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        creator_agent_id: 创建者Agent ID
        req: 记忆创建请求

    Returns:
        团队记忆响应

    Raises:
        PermissionError: 无权限
        ValueError: 团队不存在
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, creator_agent_id, "member")

    # 获取创建者
    creator_result = await db.execute(
        select(Agent).where(Agent.agent_id == creator_agent_id)
    )
    creator = creator_result.scalar_one_or_none()
    if not creator:
        raise ValueError("创建者不存在")

    # 创建记忆
    memory = Memory(
        memory_id=gen_id("mem"),
        seller_agent_id=creator_agent_id,  # 记录卖方（用于兼容个人记忆）
        team_id=team_id,
        team_access_level=req.team_access_level,
        created_by_agent_id=creator_agent_id,
        title=req.title,
        category=req.category,
        tags=req.tags,
        summary=req.summary,
        content=req.content,
        format_type=req.format_type,
        price=req.price,
        verification_data=req.verification_data
    )

    # 计算验证分数
    if req.verification_data:
        memory.verification_score = _calc_verification_score(req.verification_data)

    # 设置过期时间
    if req.expires_days:
        from datetime import datetime, timedelta
        memory.expires_at = datetime.now() + timedelta(days=req.expires_days)

    db.add(memory)

    # 更新团队记忆统计
    await db.execute(
        update(Team)
        .where(Team.team_id == team_id)
        .values(memory_count=Team.memory_count + 1)
    )

    # 更新创建者统计
    creator.memories_uploaded += 1

    await db.commit()
    await db.refresh(memory)

    # 创建初始版本快照
    from app.services.memory_service import create_memory_version
    await create_memory_version(db, memory, changelog="初始版本")
    await db.commit()

    # 增量向量化（异步）
    from app.services.memory_service import _vectorize_memory_async
    _vectorize_memory_async(memory)

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        creator_agent_id,
        "memory_created",
        f"创建了记忆: {memory.title}",
        related_id=memory.memory_id
    )

    # 构建响应
    team = await db.execute(select(Team).where(Team.team_id == team_id))
    team = team.scalar_one_or_none()

    return TeamMemoryResponse(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name,
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


async def get_team_memories(
    db: AsyncSession,
    team_id: str,
    request_agent_id: str,
    page: int = 1,
    page_size: int = 20
) -> TeamMemoryList:
    """获取团队记忆列表

    Args:
        db: 数据库会话
        team_id: 团队ID
        request_agent_id: 请求者Agent ID
        page: 页码
        page_size: 每页数量

    Returns:
        团队记忆列表

    Raises:
        PermissionError: 无权限
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, request_agent_id, "member")

    # 计算总数
    count_stmt = select(func.count()).select_from(Memory).where(
        and_(Memory.team_id == team_id, Memory.is_active == True)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 获取记忆列表
    stmt = (
        select(Memory, Agent, Team)
        .join(Agent, Memory.created_by_agent_id == Agent.agent_id)
        .outerjoin(Team, Memory.team_id == Team.team_id)
        .where(
            and_(Memory.team_id == team_id, Memory.is_active == True)
        )
        .order_by(desc(Memory.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    items = []

    for row in result:
        memory = row[0]
        creator = row[1]
        team = row[2]

        items.append(TeamMemoryResponse(
            memory_id=memory.memory_id,
            team_id=memory.team_id,
            team_name=team.name if team else None,
            created_by_agent_id=memory.created_by_agent_id,
            created_by_name=creator.name if creator else "",
            title=memory.title,
            category=memory.category,
            tags=memory.tags or [],
            summary=memory.summary,
            format_type=memory.format_type,
            price=memory.price,
            purchase_count=memory.purchase_count,
            favorite_count=memory.favorite_count,
            avg_score=memory.avg_score,
            verification_score=memory.verification_score,
            team_access_level=memory.team_access_level,
            created_at=memory.created_at,
            updated_at=memory.updated_at
        ))

    return TeamMemoryList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


async def get_team_memory_detail(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str
) -> TeamMemoryDetail:
    """获取团队记忆详情

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID

    Returns:
        团队记忆详情

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, request_agent_id, "member")

    # 获取记忆
    result = await db.execute(
        select(Memory, Agent, Team)
        .join(Agent, Memory.created_by_agent_id == Agent.agent_id)
        .outerjoin(Team, Memory.team_id == Team.team_id)
        .where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    row = result.first()

    if not row:
        raise ValueError("记忆不存在")

    memory, creator, team = row

    # 处理 content 字段
    content = memory.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except JSONDecodeError:
            content = {"raw": content}

    # 处理 verification_data 字段
    verification_data = memory.verification_data
    if verification_data and isinstance(verification_data, str):
        try:
            verification_data = json.loads(verification_data)
        except JSONDecodeError:
            verification_data = {"raw": verification_data}

    return TeamMemoryDetail(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name if creator else "",
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        content=content,
        verification_data=verification_data
    )


async def update_team_memory(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str,
    req: TeamMemoryUpdate
) -> TeamMemoryResponse:
    """更新团队记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID
        req: 更新请求

    Returns:
        更新后的团队记忆

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限（admin及以上可以修改）
    member, _ = await _check_team_permission(db, team_id, request_agent_id, "admin")

    # 获取记忆
    result = await db.execute(
        select(Memory).where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    memory = result.scalar_one_or_none()

    if not memory:
        raise ValueError("记忆不存在")

    # 提取 changelog
    changelog = req.changelog

    # 更新字段
    if req.summary is not None:
        memory.summary = req.summary
    if req.content is not None:
        memory.content = req.content
    if req.tags is not None:
        memory.tags = req.tags

    # 更新时间戳
    from datetime import datetime
    memory.updated_at = datetime.now()

    await db.commit()
    await db.refresh(memory)

    # 创建版本快照
    from app.services.memory_service import create_memory_version
    await create_memory_version(db, memory, changelog=changelog)
    await db.commit()

    # 增量向量化更新
    from app.services.memory_service import _vectorize_memory_async
    _vectorize_memory_async(memory)

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        request_agent_id,
        "memory_updated",
        f"更新了记忆: {memory.title}",
        related_id=memory.memory_id
    )

    # 构建响应
    creator_result = await db.execute(
        select(Agent).where(Agent.agent_id == memory.created_by_agent_id)
    )
    creator = creator_result.scalar_one_or_none()
    team_result = await db.execute(select(Team).where(Team.team_id == team_id))
    team = team_result.scalar_one_or_none()

    return TeamMemoryResponse(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name if creator else "",
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


async def delete_team_memory(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str
) -> None:
    """删除团队记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限（admin及以上可以删除）
    member, _ = await _check_team_permission(db, team_id, request_agent_id, "admin")

    # 获取记忆
    result = await db.execute(
        select(Memory).where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    memory = result.scalar_one_or_none()

    if not memory:
        raise ValueError("记忆不存在")

    # 软删除
    memory.is_active = False
    await db.commit()

    # 更新团队记忆统计
    await db.execute(
        update(Team)
        .where(Team.team_id == team_id)
        .values(memory_count=Team.memory_count - 1)
    )
    await db.commit()

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        request_agent_id,
        "memory_deleted",
        f"删除了记忆: {memory.title}",
        related_id=memory.memory_id
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
    # 创建活动记录（如果活动日志表存在）
    # 注意：这里假设有 TeamActivityLog 表，如果没有可以跳过或创建
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
        # 表不存在，跳过
        pass
    except Exception:
        # 其他错误，跳过
        pass
