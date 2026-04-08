"""认证模块 — 支持 Agent World 身份认证 + 原有 X-API-Key"""
import os
from typing import Optional
from fastapi import Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.db.database import get_db
from app.models.tables import Agent
from app.core.exceptions import UNAUTHORIZED

# Agent World 配置
AGENT_WORLD_VERIFY_URL = os.getenv(
    "AGENT_WORLD_VERIFY_URL", "https://world.coze.site/api/agents/verify-key"
)
X_SITE_ID = os.getenv("X_SITE_ID", "YOUR_SITE_ID")
X_SITE_SECRET = os.getenv("X_SITE_SECRET", "YOUR_SITE_SECRET")


async def _lookup_agent(db: AsyncSession, api_key: str) -> Optional[Agent]:
    """Helper: Look up agent by API key"""
    result = await db.execute(
        select(Agent).where(Agent.api_key == api_key)
    )
    agent = result.scalar_one_or_none()
    if agent and agent.is_active:
        return agent
    return None


async def _lookup_agent_by_world_id(db: AsyncSession, agent_world_id: str) -> Optional[Agent]:
    """Helper: Look up agent by agent_world_id"""
    result = await db.execute(
        select(Agent).where(Agent.agent_world_id == agent_world_id)
    )
    agent = result.scalar_one_or_none()
    if agent and agent.is_active:
        return agent
    return None


async def _verify_agent_world_key(api_key: str) -> Optional[dict]:
    """调用 Agent World 验证接口，返回验证结果或 None"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                AGENT_WORLD_VERIFY_URL,
                json={"api_key": api_key},
                headers={
                    "x-site-id": X_SITE_ID,
                    "x-site-secret": X_SITE_SECRET,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid"):
                    return data
            return None
    except httpx.HTTPError:
        return None


async def _get_or_create_from_agent_world(api_key: str, db: AsyncSession) -> Optional[Agent]:
    """验证 Agent World API Key，自动创建或返回已有 Agent"""
    result = await _verify_agent_world_key(api_key)
    if not result:
        return None

    world_id = result.get("agent_id") or result.get("id")
    name = result.get("name") or f"Agent-{world_id}"

    # 先按 agent_world_id 查找
    agent = await _lookup_agent_by_world_id(db, world_id)
    if agent:
        return agent

    # 创建新 Agent
    agent = Agent(
        name=name,
        api_key=f"aw_{world_id}",  # 本地占位 key，实际认证走 Agent World
        agent_world_id=world_id,
        role="user",
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def _resolve_agent(
    x_api_key: Optional[str],
    agent_auth_api_key: Optional[str],
    db: AsyncSession,
) -> Optional[Agent]:
    """统一认证解析：优先 Agent World，降级 X-API-Key"""
    if agent_auth_api_key:
        agent = await _get_or_create_from_agent_world(agent_auth_api_key, db)
        if agent:
            return agent

    if x_api_key:
        agent = await _lookup_agent(db, x_api_key)
        if agent:
            return agent

    return None


async def get_current_agent(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    agent_auth_api_key: Optional[str] = Header(None, alias="agent-auth-api-key"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """认证中间件 — Agent World 优先，降级 X-API-Key"""
    agent = await _resolve_agent(x_api_key, agent_auth_api_key, db)
    if not agent:
        raise UNAUTHORIZED
    return agent


async def get_optional_agent(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    agent_auth_api_key: Optional[str] = Header(None, alias="agent-auth-api-key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[Agent]:
    """可选认证 — 有 Key 就识别，没有就返回 None"""
    return await _resolve_agent(x_api_key, agent_auth_api_key, db)


async def get_anonymous_or_agent(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    agent_auth_api_key: Optional[str] = Header(None, alias="agent-auth-api-key"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """匿名或已认证 Agent — 搜索用

    优先 Agent World 认证，降级 X-API-Key，最后返回匿名 Agent
    """
    agent = await _resolve_agent(x_api_key, agent_auth_api_key, db)
    if agent:
        return agent

    # 返回匿名 Agent（临时对象）
    return Agent(
        agent_id="anonymous",
        name="Anonymous",
        api_key="anonymous",
        role="user",
        is_active=True,
    )
