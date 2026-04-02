
"""认证模块"""
from typing import Optional
from fastapi import Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.tables import Agent
from app.core.exceptions import UNAUTHORIZED, FORBIDDEN


async def _lookup_agent(db: AsyncSession, api_key: str) -> Optional[Agent]:
    """Helper: Look up agent by API key"""
    result = await db.execute(
        select(Agent).where(Agent.api_key == api_key)
    )
    agent = result.scalar_one_or_none()
    if agent and agent.is_active:
        return agent
    return None


async def get_current_agent(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    """认证中间件，通过 X-API-Key 获取当前 Agent"""
    agent = await _lookup_agent(db, x_api_key)
    if not agent:
        raise UNAUTHORIZED
    return agent


async def get_optional_agent(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Optional[Agent]:
    """可选认证 — 有 Key 就识别，没有就返回 None"""
    if not x_api_key:
        return None
    return await _lookup_agent(db, x_api_key)
