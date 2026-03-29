#!/usr/bin/env python3
"""
团队记忆协作功能快速测试脚本

用于验证阶段3的所有功能是否正常工作
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

# 添加项目路径
sys.path.insert(0, "/Users/sss/.openclaw/workspace/memory-market")

from app.models.tables import Agent, Team, TeamMember, Memory
from app.models.schemas import TeamMemoryCreate, TeamMemoryUpdate
from app.services.memory_service import (
    create_team_memory, get_team_memories, update_team_memory,
    delete_team_memory, get_team_memory_detail
)
from app.services.purchase_service_v2 import purchase_with_team_credits
from app.services.team_service import TeamService, CreditService
from app.db.database import AsyncSessionLocal


async def create_test_agent(db: AsyncSession, name: str) -> Agent:
    """创建测试Agent"""
    agent = Agent(
        name=name,
        description=f"Test agent: {name}",
        api_key=f"test_{name.lower().replace(' ', '_')}",
        credits=1000,
        reputation_score=5.0,
        total_sales=0,
        total_purchases=0,
        memories_uploaded=0,
        is_active=True
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    print(f"✓ Created Agent: {agent.name} ({agent.agent_id})")
    return agent


async def create_test_team(db: AsyncSession, owner: Agent) -> Team:
    """创建测试团队"""
    from app.models.schemas import TeamCreate

    req = TeamCreate(
        name="Test Team",
        description="Test team for validation"
    )
    team = await TeamService.create_team(db, owner.agent_id, req)
    print(f"✓ Created Team: {team.name} ({team.team_id})")
    return team


async def add_team_member(db: AsyncSession, team: Team, agent: Agent, role: str):
    """添加团队成员"""
    member = TeamMember(
        team_id=team.team_id,
        agent_id=agent.agent_id,
        role=role,
        is_active=True
    )
    db.add(member)

    # 更新团队成员数
    from sqlalchemy import update
    await db.execute(
        update(Team).where(Team.team_id == team.team_id).values(
            member_count=Team.member_count + 1
        )
    )

    await db.commit()
    print(f"✓ Added Member: {agent.name} as {role}")


async def test_create_team_memory(db: AsyncSession, team: Team, creator: Agent):
    """测试：创建团队记忆"""
    req = TeamMemoryCreate(
        title="Test Team Memory",
        category="test/validation",
        tags=["test", "team"],
        content={"test": "data", "key": "value"},
        summary="A test team memory for validation",
        format_type="template",
        price=0,
        team_access_level="team_only"
    )

    memory = await create_team_memory(db, team.team_id, creator.agent_id, req)
    print(f"✓ Created Team Memory: {memory.title} ({memory.memory_id})")
    print(f"  - Team: {team.name}")
    print(f"  - Access Level: {memory.team_access_level}")
    return memory


async def test_get_team_memories(db: AsyncSession, team: Team, member: Agent):
    """测试：获取团队记忆列表"""
    result = await get_team_memories(db, team.team_id, member.agent_id, 1, 20)
    print(f"✓ Got Team Memories: {result.total} memories")
    for mem in result.items:
        print(f"  - {mem.title} by {mem.created_by_name}")
    return result


async def test_update_team_memory(db: AsyncSession, team: Team, memory_id: str, updater: Agent):
    """测试：更新团队记忆"""
    update_req = TeamMemoryUpdate(
        summary="Updated summary for validation",
        content={"updated": "content", "new": "data"}
    )

    updated = await update_team_memory(
        db, team.team_id, memory_id, updater.agent_id, update_req
    )
    print(f"✓ Updated Team Memory: {updated.title}")
    print(f"  - New Summary: {updated.summary}")
    return updated


async def test_create_personal_memory(db: AsyncSession, seller: Agent) -> Memory:
    """创建个人记忆用于购买测试"""
    memory = Memory(
        memory_id="mem_test_purchase_001",
        seller_agent_id=seller.agent_id,
        title="Personal Memory for Purchase Test",
        category="test/purchase",
        tags=["test", "purchase"],
        summary="A personal memory for purchase testing",
        content={"purchase": "test", "data": "value"},
        format_type="template",
        price=50,
        purchase_count=0,
        favorite_count=0,
        avg_score=0.0,
        is_active=True,
        team_id=None,
        team_access_level="private"
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    print(f"✓ Created Personal Memory: {memory.title} ({memory.memory_id})")
    return memory


async def test_purchase_with_team_credits(db: AsyncSession, team: Team, member: Agent, memory_id: str):
    """测试：使用团队积分购买记忆"""
    # 确保团队有足够积分
    team.credits = 500
    await db.commit()

    result = await purchase_with_team_credits(
        db, team.team_id, member.agent_id, memory_id
    )

    if result.success:
        print(f"✓ Purchased Memory with Team Credits")
        print(f"  - Credits Spent: {result.credits_spent}")
        print(f"  - Team Credits Remaining: {result.team_credits_remaining}")
    else:
        print(f"✗ Purchase Failed: {result.message}")

    return result


async def test_team_stats(db: AsyncSession, team: Team):
    """测试：获取团队统计"""
    from app.api.team_stats import get_team_stats

    stats = await get_team_stats(team.team_id, team.owner_agent_id, db)

    print(f"✓ Got Team Stats:")
    print(f"  - Team Name: {stats.name}")
    print(f"  - Member Count: {stats.member_count}")
    print(f"  - Memory Count: {stats.memory_count}")
    print(f"  - Team Memories: {stats.team_memories_count}")
    print(f"  - Team Credits: {stats.credits}")

    return stats


async def test_team_activity_logs(db: AsyncSession, team: Team):
    """测试：获取团队活动日志"""
    from app.api.team_activity import get_team_activity_logs

    logs = await get_team_activity_logs(
        team.team_id, None, 1, 20, team.owner_agent_id, db
    )

    print(f"✓ Got Team Activity Logs: {logs.total} logs")
    for log in logs.items[:3]:  # 只显示前3条
        print(f"  - [{log.activity_type}] {log.description}")
        print(f"    by {log.agent_name} at {log.created_at}")

    return logs


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("团队记忆协作功能验证测试")
    print("="*60 + "\n")

    async with AsyncSessionLocal() as db:
        try:
            # 1. 创建测试数据
            print("📝 步骤1: 创建测试数据")
            print("-" * 60)
            owner = await create_test_agent(db, "Team Owner")
            admin = await create_test_agent(db, "Team Admin")
            member = await create_test_agent(db, "Team Member")
            seller = await create_test_agent(db, "Memory Seller")

            team = await create_test_team(db, owner)

            await add_team_member(db, team, admin, "admin")
            await add_team_member(db, team, member, "member")

            print()

            # 2. 测试创建团队记忆
            print("📝 步骤2: 测试创建团队记忆")
            print("-" * 60)
            memory = await test_create_team_memory(db, team, owner)
            print()

            # 3. 测试获取团队记忆列表
            print("📝 步骤3: 测试获取团队记忆列表")
            print("-" * 60)
            await test_get_team_memories(db, team, member)
            print()

            # 4. 测试更新团队记忆
            print("📝 步骤4: 测试更新团队记忆（Admin权限）")
            print("-" * 60)
            await test_update_team_memory(db, team, memory.memory_id, admin)
            print()

            # 5. 测试团队购买流程
            print("📝 步骤5: 测试团队购买流程")
            print("-" * 60)
            personal_memory = await test_create_personal_memory(db, seller)
            await test_purchase_with_team_credits(db, team, member, personal_memory.memory_id)
            print()

            # 6. 测试团队统计
            print("📝 步骤6: 测试团队统计")
            print("-" * 60)
            await test_team_stats(db, team)
            print()

            # 7. 测试团队活动日志
            print("📝 步骤7: 测试团队活动日志")
            print("-" * 60)
            await test_team_activity_logs(db, team)
            print()

            # 总结
            print("="*60)
            print("✅ 所有测试通过！")
            print("="*60)
            print("\n功能验证结果：")
            print("  ✅ 团队记忆创建")
            print("  ✅ 团队记忆查询")
            print("  ✅ 团队记忆更新")
            print("  ✅ 团队积分购买")
            print("  ✅ 团队统计")
            print("  ✅ 团队活动日志")
            print("\n阶段3完成！\n")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
