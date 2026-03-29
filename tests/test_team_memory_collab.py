"""团队记忆协作功能测试"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models.tables import Base, Agent, Team, TeamMember, Memory, Purchase, TeamCreditTransaction, TeamActivityLog
from app.core.config import settings
from app.db.database import get_db
from app.services.memory_service import (
    create_team_memory, get_team_memories, update_team_memory,
    delete_team_memory, get_team_memory_detail
)
from app.services.purchase_service_v2 import purchase_with_team_credits
from app.models.schemas import TeamMemoryCreate, TeamMemoryUpdate


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Fixture: 数据库会话
@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Fixture: 测试Agent
@pytest.fixture
async def test_agent(db_session: AsyncSession):
    """创建测试Agent"""
    agent = Agent(
        name="Test Agent",
        description="Test agent for unit tests",
        api_key="test_api_key_123",
        credits=1000,
        reputation_score=5.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


# Fixture: 测试团队
@pytest.fixture
async def test_team(db_session: AsyncSession, test_agent: Agent):
    """创建测试团队"""
    team = Team(
        name="Test Team",
        description="Test team for unit tests",
        owner_agent_id=test_agent.agent_id,
        member_count=1,
        memory_count=0,
        credits=500,
        total_earned=0,
        total_spent=0,
        is_active=True
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    # 添加owner为成员
    member = TeamMember(
        team_id=team.team_id,
        agent_id=test_agent.agent_id,
        role="owner",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()

    return team


# Fixture: 测试Admin成员
@pytest.fixture
async def test_admin_member(db_session: AsyncSession, test_team: Team):
    """创建测试Admin成员"""
    agent = Agent(
        name="Admin Agent",
        description="Admin agent for unit tests",
        api_key="admin_api_key_456",
        credits=500,
        reputation_score=4.5,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    member = TeamMember(
        team_id=test_team.team_id,
        agent_id=agent.agent_id,
        role="admin",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()

    return agent


# Fixture: 测试个人记忆（用于购买测试）
@pytest.fixture
async def test_personal_memory(db_session: AsyncSession, test_agent: Agent):
    """创建测试个人记忆"""
    memory = Memory(
        memory_id="mem_test_123",
        seller_agent_id=test_agent.agent_id,
        title="Test Personal Memory",
        category="test/category",
        tags=["test", "personal"],
        summary="A test personal memory",
        content={"key": "value"},
        format_type="template",
        price=100,
        purchase_count=0,
        favorite_count=0,
        avg_score=0.0,
        is_active=True,
        team_id=None,
        team_access_level="private"
    )
    db_session.add(memory)
    await db_session.commit()
    await db_session.refresh(memory)
    return memory


# ============ 测试：记忆可见性控制 ============

@pytest.mark.asyncio
async def test_create_team_memory_visibility(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试创建团队记忆的可见性控制"""
    req = TeamMemoryCreate(
        title="Test Team Memory",
        category="test/team",
        tags=["test", "team"],
        content={"key": "value"},
        summary="A test team memory",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    assert memory.team_id == test_team.team_id
    assert memory.team_access_level == "team_only"
    assert memory.created_by_agent_id == test_agent.agent_id


@pytest.mark.asyncio
async def test_private_memory_not_visible_in_team(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试个人记忆不显示在团队记忆列表中"""
    # 创建个人记忆
    personal_memory = Memory(
        memory_id="mem_personal_001",
        seller_agent_id=test_agent.agent_id,
        title="Personal Memory",
        category="test/personal",
        tags=["test"],
        summary="Personal memory",
        content={"key": "value"},
        format_type="template",
        price=50,
        purchase_count=0,
        favorite_count=0,
        avg_score=0.0,
        is_active=True,
        team_id=None,
        team_access_level="private"
    )
    db_session.add(personal_memory)
    await db_session.commit()

    # 查询团队记忆
    result = await get_team_memories(db_session, test_team.team_id, test_agent.agent_id, 1, 20)

    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_team_only_memory_visible_to_members(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试 team_only 记忆对团队成员可见"""
    req = TeamMemoryCreate(
        title="Team Only Memory",
        category="test/team",
        tags=["test"],
        content={"key": "value"},
        summary="Team only memory",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 团队成员可以查看
    result = await get_team_memories(db_session, test_team.team_id, test_agent.agent_id, 1, 20)

    assert len(result.items) == 1
    assert result.items[0].team_access_level == "team_only"


# ============ 测试：团队记忆 CRUD ============

@pytest.mark.asyncio
async def test_create_team_memory(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试创建团队记忆"""
    req = TeamMemoryCreate(
        title="New Team Memory",
        category="test/new",
        tags=["new"],
        content={"data": "test"},
        summary="New team memory",
        format_type="strategy",
        price=100,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    assert memory.memory_id is not None
    assert memory.title == "New Team Memory"
    assert memory.team_id == test_team.team_id


@pytest.mark.asyncio
async def test_get_team_memories(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试获取团队记忆列表"""
    # 创建多个记忆
    for i in range(3):
        req = TeamMemoryCreate(
            title=f"Team Memory {i+1}",
            category="test/list",
            tags=["test"],
            content={"index": i},
            summary=f"Memory {i+1}",
            format_type="template",
            price=50,
            team_access_level="team_only"
        )
        await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 获取列表
    result = await get_team_memories(db_session, test_team.team_id, test_agent.agent_id, 1, 20)

    assert result.total == 3
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_get_team_memory_detail(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试获取团队记忆详情"""
    req = TeamMemoryCreate(
        title="Detail Memory",
        category="test/detail",
        tags=["test"],
        content={"secret": "data"},
        summary="Memory with details",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 获取详情
    detail = await get_team_memory_detail(
        db_session, test_team.team_id, memory.memory_id, test_agent.agent_id
    )

    assert detail.memory_id == memory.memory_id
    assert detail.content == {"secret": "data"}


@pytest.mark.asyncio
async def test_update_team_memory_admin(db_session: AsyncSession, test_team: Team, test_admin_member: Agent):
    """测试Admin更新团队记忆"""
    # 创建记忆
    req = TeamMemoryCreate(
        title="Original Title",
        category="test/update",
        tags=["test"],
        content={"old": "data"},
        summary="Original summary",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_admin_member.agent_id, req)

    # 更新
    update_req = TeamMemoryUpdate(
        summary="Updated summary",
        content={"new": "data"}
    )

    updated = await update_team_memory(
        db_session, test_team.team_id, memory.memory_id,
        test_admin_member.agent_id, update_req
    )

    assert updated.summary == "Updated summary"


@pytest.mark.asyncio
async def test_member_cannot_update_memory(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试普通成员不能更新记忆"""
    # 添加普通成员
    member_agent = Agent(
        name="Member Agent",
        description="Member agent",
        api_key="member_api_key",
        credits=500,
        reputation_score=4.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(member_agent)
    await db_session.commit()

    member = TeamMember(
        team_id=test_team.team_id,
        agent_id=member_agent.agent_id,
        role="member",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()

    # 创建记忆
    req = TeamMemoryCreate(
        title="Test Memory",
        category="test/perm",
        tags=["test"],
        content={"key": "value"},
        summary="Test memory",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 尝试更新（应该失败）
    update_req = TeamMemoryUpdate(summary="New summary")

    with pytest.raises(PermissionError):
        await update_team_memory(
            db_session, test_team.team_id, memory.memory_id,
            member_agent.agent_id, update_req
        )


@pytest.mark.asyncio
async def test_delete_team_memory(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试删除团队记忆"""
    # 创建记忆
    req = TeamMemoryCreate(
        title="To Delete",
        category="test/delete",
        tags=["test"],
        content={"key": "value"},
        summary="Memory to delete",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 删除
    await delete_team_memory(
        db_session, test_team.team_id, memory.memory_id, test_agent.agent_id
    )

    # 验证已删除（软删除）
    result = await db_session.execute(
        select(Memory).where(Memory.memory_id == memory.memory_id)
    )
    deleted_memory = result.scalar_one_or_none()

    assert deleted_memory is not None
    assert deleted_memory.is_active is False


# ============ 测试：团队购买流程 ============

@pytest.mark.asyncio
async def test_purchase_with_team_credits(db_session: AsyncSession, test_team: Team, test_personal_memory: Memory):
    """测试使用团队积分购买记忆"""
    # 创建团队成员
    member_agent = Agent(
        name="Buyer Agent",
        description="Buyer agent",
        api_key="buyer_api_key",
        credits=0,
        reputation_score=4.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(member_agent)
    await db_session.commit()

    member = TeamMember(
        team_id=test_team.team_id,
        agent_id=member_agent.agent_id,
        role="member",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()

    # 执行购买
    result = await purchase_with_team_credits(
        db_session, test_team.team_id, member_agent.agent_id,
        test_personal_memory.memory_id
    )

    assert result.success is True
    assert result.credits_spent == test_personal_memory.price

    # 验证团队积分已扣减
    team = await db_session.execute(select(Team).where(Team.team_id == test_team.team_id))
    team = team.scalar_one_or_none()

    assert team.credits == 400  # 500 - 100


@pytest.mark.asyncio
async def test_cannot_purchase_team_own_memory(db_session: AsyncSession, test_team: Team, test_agent: Agent):
    """测试团队不能购买自己的记忆"""
    # 创建团队记忆
    req = TeamMemoryCreate(
        title="Team Memory",
        category="test/team",
        tags=["test"],
        content={"key": "value"},
        summary="Team memory",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, test_agent.agent_id, req)

    # 尝试购买自己的记忆（应该失败）
    with pytest.raises(ValueError, match="团队记忆无需购买"):
        await purchase_with_team_credits(
            db_session, test_team.team_id, test_agent.agent_id, memory.memory_id
        )


@pytest.mark.asyncio
async def test_team_insufficient_credits(db_session: AsyncSession, test_team: Team, test_personal_memory: Memory):
    """测试团队积分不足"""
    # 减少团队积分
    team = await db_session.execute(select(Team).where(Team.team_id == test_team.team_id))
    team = team.scalar_one_or_none()
    team.credits = 50  # 不足以购买 100 的记忆
    await db_session.commit()

    # 创建成员
    member_agent = Agent(
        name="Poor Buyer",
        description="Poor buyer",
        api_key="poor_api_key",
        credits=0,
        reputation_score=4.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(member_agent)
    await db_session.commit()

    member = TeamMember(
        team_id=test_team.team_id,
        agent_id=member_agent.agent_id,
        role="member",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()

    # 尝试购买（应该失败）
    with pytest.raises(ValueError, match="团队积分不足"):
        await purchase_with_team_credits(
            db_session, test_team.team_id, member_agent.agent_id,
            test_personal_memory.memory_id
        )


# ============ 测试：权限控制 ============

@pytest.mark.asyncio
async def test_non_member_cannot_access_team_memory(db_session: AsyncSession, test_team: Team):
    """测试非团队成员不能访问团队记忆"""
    # 创建非团队成员
    outsider_agent = Agent(
        name="Outsider",
        description="Outsider agent",
        api_key="outsider_api_key",
        credits=500,
        reputation_score=4.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(outsider_agent)
    await db_session.commit()

    # 创建团队记忆
    owner_agent = Agent(
        name="Owner",
        description="Owner agent",
        api_key="owner_api_key",
        credits=500,
        reputation_score=5.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db_session.add(owner_agent)
    await db_session.commit()

    owner_member = TeamMember(
        team_id=test_team.team_id,
        agent_id=owner_agent.agent_id,
        role="owner",
        is_active=True
    )
    db_session.add(owner_member)
    await db_session.commit()

    req = TeamMemoryCreate(
        title="Secret Memory",
        category="test/secret",
        tags=["test"],
        content={"secret": "data"},
        summary="Secret team memory",
        format_type="template",
        price=50,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db_session, test_team.team_id, owner_agent.agent_id, req)

    # 非成员尝试访问（应该失败）
    with pytest.raises(PermissionError, match="不是团队成员"):
        await get_team_memories(db_session, test_team.team_id, outsider_agent.agent_id, 1, 20)
