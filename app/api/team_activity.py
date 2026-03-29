"""团队活动日志 API"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime

from app.api.dependencies import get_db, get_current_agent
from app.models.tables import Agent, Team, TeamMember, TeamActivityLog
from app.models.schemas import TeamActivityLog as TeamActivityLogSchema, TeamActivityList
from app.core.exceptions import AppError


router = APIRouter(prefix="/teams/{team_id}/activity", tags=["team-activity"])


@router.get("/", response_model=TeamActivityList)
async def get_team_activity_logs(
    team_id: str,
    activity_type: Optional[str] = Query(None, description="活动类型过滤"),
    agent_id: Optional[str] = Query(None, description="成员ID过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取团队活动日志

    Args:
        team_id: 团队ID
        activity_type: 活动类型过滤（可选）
        agent_id: 成员ID过滤（可选）
        page: 页码
        page_size: 每页数量
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 构建查询
    query = select(TeamActivityLog, Agent).outerjoin(
        Agent, TeamActivityLog.agent_id == Agent.agent_id
    ).where(TeamActivityLog.team_id == team_id)

    # 应用过滤条件
    if activity_type:
        query = query.where(TeamActivityLog.activity_type == activity_type)
    if agent_id:
        query = query.where(TeamActivityLog.agent_id == agent_id)

    # 计算总数
    count_query = select(func.count()).select_from(TeamActivityLog).where(
        TeamActivityLog.team_id == team_id
    )
    if activity_type:
        count_query = count_query.where(TeamActivityLog.activity_type == activity_type)
    if agent_id:
        count_query = count_query.where(TeamActivityLog.agent_id == agent_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取记录（按时间降序）
    query = query.order_by(desc(TeamActivityLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)

    items = []
    for row in result:
        activity = row[0]
        agent = row[1]

        items.append(TeamActivityLogSchema(
            activity_id=activity.activity_id,
            team_id=activity.team_id,
            agent_id=activity.agent_id,
            agent_name=agent.name if agent else None,
            activity_type=activity.activity_type,
            description=activity.description,
            related_id=activity.related_id,
            extra_data=activity.extra_data,
            created_at=activity.created_at
        ))

    return TeamActivityList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/types")
async def get_activity_types(
    team_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取所有活动类型（用于筛选）

    Args:
        team_id: 团队ID
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 获取所有活动类型
    result = await db.execute(
        select(TeamActivityLog.activity_type, func.count().label("count"))
        .where(TeamActivityLog.team_id == team_id)
        .group_by(TeamActivityLog.activity_type)
        .order_by(desc(func.count()))
    )

    types = []
    for row in result:
        types.append({
            "type": row[0],
            "count": row[1]
        })

    return {
        "activity_types": types
    }


@router.post("/log", status_code=201)
async def log_custom_activity(
    team_id: str,
    activity_type: str = Query(..., description="活动类型"),
    description: str = Query(..., description="活动描述"),
    related_id: Optional[str] = Query(None, description="关联ID"),
    extra_data: Optional[dict] = None,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """记录自定义团队活动

    Args:
        team_id: 团队ID
        activity_type: 活动类型
        description: 活动描述
        related_id: 关联ID（可选）
        extra_data: 额外信息（可选）
    """
    # 检查团队成员权限
    from app.services.memory_service import _check_team_permission
    try:
        await _check_team_permission(db, team_id, current_agent.agent_id, "member")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队")
    except ValueError:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 创建活动记录
    import uuid
    activity_id = f"act_{uuid.uuid4().hex[:12]}"

    activity = TeamActivityLog(
        activity_id=activity_id,
        team_id=team_id,
        agent_id=current_agent.agent_id,
        activity_type=activity_type,
        description=description,
        related_id=related_id,
        extra_data=extra_data
    )
    db.add(activity)
    await db.commit()

    return {
        "success": True,
        "message": "活动记录成功",
        "activity_id": activity_id
    }
