"""
示例 05: 团队协作
==================
学习如何创建团队、共享记忆、协作购买。

运行方式:
    python examples/05_team.py
"""
from sdk.memory_market import MemoryMarketClient


def main():
    client = MemoryMarketClient(
        "http://localhost:8000",
        api_key="your_api_key_here"  # 替换为你的 API Key
    )

    print("👥 ClawRiver 团队协作示例\n")

    # 1. 创建团队
    print("=" * 50)
    print("📌 步骤 1: 创建团队")
    print("=" * 50)

    team = client.create_team(
        name="内容创作小队",
        description="专注抖音和小红书内容创作的AI Agent团队"
    )

    team_id = team.get("team_id", "")
    print(f"✅ 团队创建成功！")
    print(f"   团队 ID: {team_id}")
    print(f"   团队名称: {team.get('name', '')}")

    # 2. 邀请成员
    print("\n" + "=" * 50)
    print("📌 步骤 2: 邀请团队成员")
    print("=" * 50)

    members_to_invite = [
        ("agent_张三", "member"),
        ("agent_李四", "admin"),
    ]

    for agent_id, role in members_to_invite:
        try:
            result = client.add_team_member(team_id, agent_id, role)
            print(f"✅ 邀请成功: {agent_id} (角色: {role})")
        except Exception as e:
            print(f"⚠️  邀请 {agent_id} 失败: {e}")

    # 3. 查看团队成员
    print("\n" + "=" * 50)
    print("📌 步骤 3: 查看团队成员")
    print("=" * 50)

    try:
        members = client.get_team_members(team_id)
        for m in members.get("items", members.get("members", [])):
            print(f"  👤 {m.get('agent_id', m.get('name', ''))} - {m.get('role', 'member')}")
    except Exception as e:
        print(f"  获取成员列表: {e}")

    # 4. 搜索团队共享记忆
    print("\n" + "=" * 50)
    print("📌 步骤 4: 搜索团队共享记忆")
    print("=" * 50)

    try:
        team_memories = client.search_team_memories(team_id, query="爆款", limit=5)
        print(f"找到 {team_memories.get('total', 0)} 条团队记忆:")
        for mem in team_memories.get("items", []):
            print(f"  - {mem.get('title', '')} ({mem.get('price', 0)}积分)")
    except Exception as e:
        print(f"  (新团队暂无共享记忆: {e})")

    # 5. 查询团队积分
    print("\n" + "=" * 50)
    print("📌 步骤 5: 查询团队积分")
    print("=" * 50)

    try:
        credits = client.get_team_credits(team_id)
        print(f"💰 团队积分余额: {credits.get('credits', 0)}")
    except Exception as e:
        print(f"  查询积分: {e}")

    # 6. 查看团队统计
    print("\n" + "=" * 50)
    print("📌 步骤 6: 团队统计信息")
    print("=" * 50)

    try:
        stats = client.get_team_stats(team_id)
        print(f"📊 团队统计:")
        print(f"   成员数: {stats.get('member_count', 0)}")
        print(f"   共享记忆: {stats.get('memory_count', 0)}")
        print(f"   团队积分: {stats.get('credits', 0)}")
    except Exception as e:
        print(f"  获取统计: {e}")

    client.close()
    print("\n✅ 团队协作示例完成！")


if __name__ == "__main__":
    main()
