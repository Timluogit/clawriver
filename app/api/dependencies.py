"""API依赖注入 - 权限验证中间件"""
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.tables import Agent, Team, TeamMember
from app.core.auth import get_current_agent
from app.core.exceptions import FORBIDDEN, NOT_FOUND


async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db)
) -> Team:
    """获取团队"""
    result = await db.execute(
        select(Team).where(Team.team_id == team_id)
    )
    team = result.scalar_one_or_none()

    if not team:
        raise NOT_FOUND

    return team


async def get_team_member(
    member_id: int,
    team: Team = Depends(get_team),
    db: AsyncSession = Depends(get_db)
) -> TeamMember:
    """获取团队成员"""
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.team_id == team.team_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise NOT_FOUND

    return member


async def require_team_member(
    team: Team = Depends(get_team),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> TeamMember:
    """验证团队成员

    必须是团队成员（包括 owner/admin/member）
    """
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.team_id,
            TeamMember.agent_id == agent.agent_id,
            TeamMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise FORBIDDEN

    return member


async def require_team_admin(
    team: Team = Depends(get_team),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> TeamMember:
    """验证团队管理员

    必须是 owner 或 admin
    """
    member = await require_team_member(team, agent, db)

    if member.role not in ["owner", "admin"]:
        raise FORBIDDEN

    return member


async def require_team_owner(
    team: Team = Depends(get_team),
    agent: Agent = Depends(get_current_agent)
) -> TeamMember:
    """验证团队所有者

    必须是 owner
    """
    if team.owner_agent_id != agent.agent_id:
        raise FORBIDDEN

    # 返回 owner 的 member 记录
    # 这里为了简单，返回一个模拟对象
    return TeamMember(
        id=0,
        team_id=team.team_id,
        agent_id=agent.agent_id,
        role="owner",
        is_active=True
    )


async def require_team_role(
    allowed_roles: list[str]
):
    """通用角色验证

    Args:
        allowed_roles: 允许的角色列表，如 ["owner", "admin"]
    """
    async def check_role(
        team: Team = Depends(get_team),
        agent: Agent = Depends(get_current_agent),
        db: AsyncSession = Depends(get_db)
    ) -> TeamMember:
        member = await require_team_member(team, agent, db)

        if member.role not in allowed_roles:
            raise FORBIDDEN

        return member

    return check_role


def check_admin_role(agent: Agent):
    """检查管理员角色（同步版本）
    
    Args:
        agent: 要检查的 Agent 对象
    
    Raises:
        FORBIDDEN: 如果不是管理员或版主
    """
    if agent.role not in ("admin", "moderator"):
        raise FORBIDDEN


async def require_admin(
    agent: Agent = Depends(get_current_agent)
) -> Agent:
    """验证管理员权限

    必须是系统管理员
    """
    check_admin_role(agent)
    return agent
