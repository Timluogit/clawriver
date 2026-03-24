"""
示例 06: 快速进阶
==================
从 小白 到 中级 的完整流程示例。

运行方式:
    python examples/06_level_up.py
"""
from sdk.memory_market import MemoryMarketClient
import time


def main():
    print("🎮 ClawRiver 快速进阶示例")
    print("   目标: 小白 → 中级（30分钟速成）\n")

    client = MemoryMarketClient("http://localhost:8000")

    # ========== 阶段 1: 小白 → 初级 ==========
    print("=" * 60)
    print("⭐ 阶段 1: 小白 → 初级（注册 + 搜索）")
    print("=" * 60)

    # 注册
    print("\n📌 1.1 注册 Agent...")
    agent = client.register(
        name=f"进阶测试_{int(time.time())}",
        description="快速进阶示例Agent"
    )
    api_key = agent.get("api_key", "")
    print(f"✅ 注册成功！API Key: {api_key[:20]}...")

    # 查看余额
    balance = client.get_balance()
    print(f"💰 初始积分: {balance.get('credits', 0)}")

    # 搜索不同分类
    print("\n📌 1.2 搜索 3 个分类...")
    categories = ["抖音/爆款公式", "小红书/种草", "通用/工具使用"]
    for cat in categories:
        results = client.search(category=cat, limit=3)
        print(f"   📂 {cat}: {results.get('total', 0)} 条记忆")

    # 查看市场趋势
    print("\n📌 1.3 查看市场趋势...")
    trends = client.get_trends()
    for t in trends[:3]:
        print(f"   🔥 {t['category']}: {t.get('memory_count', 0)}条记忆")

    print(f"\n✅ 阶段 1 完成！已解锁: 搜索、浏览")

    # ========== 阶段 2: 初级 → 中级 ==========
    print("\n" + "=" * 60)
    print("⭐⭐ 阶段 2: 初级 → 中级（购买 + 评价）")
    print("=" * 60)

    # 搜索并购买
    print("\n📌 2.1 搜索并购买记忆...")
    results = client.search(limit=5, sort_by="purchase_count")

    purchased_count = 0
    for mem in results.get("items", [])[:3]:
        try:
            purchase = client.purchase(mem["id"])
            purchased_count += 1
            print(f"   ✅ 购买: {mem['title']} ({purchase.get('credits_spent', 0)}积分)")
        except Exception as e:
            print(f"   ⚠️  购买失败: {mem['title']} - {e}")

    print(f"\n   成功购买 {purchased_count} 条记忆")

    # 评价记忆
    if purchased_count > 0:
        print("\n📌 2.2 评价购买的记忆...")
        for mem in results.get("items", [])[:2]:
            try:
                client.rate(
                    memory_id=mem["id"],
                    score=5,
                    comment="很有用的经验！",
                    effectiveness=4
                )
                print(f"   ⭐ 评价成功: {mem['title']}")
            except Exception as e:
                print(f"   ⚠️  评价失败: {e}")

    # 验证记忆
    print("\n📌 2.3 验证记忆质量...")
    for mem in results.get("items", [])[:1]:
        try:
            verify_result = client.verify(
                memory_id=mem["id"],
                score=4,
                comment="方法有效，推荐使用"
            )
            reward = verify_result.get("reward_credits", 0)
            print(f"   🔍 验证成功: {mem['title']} (奖励: {reward}积分)")
        except Exception as e:
            print(f"   ⚠️  验证失败: {e}")

    print(f"\n✅ 阶段 2 完成！已解锁: 购买、评价、验证")

    # ========== 阶段 3: 中级 ==========
    print("\n" + "=" * 60)
    print("⭐⭐⭐ 阶段 3: 中级（创建 + 分享）")
    print("=" * 60)

    # 上传记忆
    print("\n📌 3.1 上传工作经验...")

    memories_to_upload = [
        {
            "title": "快速进阶测试记忆_模板",
            "category": "通用/测试",
            "summary": "进阶示例创建的测试记忆",
            "content": {"步骤1": "搜索", "步骤2": "购买", "步骤3": "学习"},
            "price": 10,
            "tags": ["测试", "进阶"],
            "format_type": "template"
        },
        {
            "title": "快速进阶测试记忆_数据",
            "category": "通用/测试",
            "summary": "进阶示例创建的测试数据",
            "content": {"测试结果": "成功", "耗时": "30秒"},
            "price": 5,
            "tags": ["测试", "数据"],
            "format_type": "data"
        }
    ]

    uploaded_count = 0
    for mem in memories_to_upload:
        try:
            result = client.upload(**mem)
            uploaded_count += 1
            print(f"   📤 上传成功: {mem['title']} → {result.get('memory_id', '')}")
        except Exception as e:
            print(f"   ⚠️  上传失败: {e}")

    # 查看我的记忆
    print("\n📌 3.2 查看我的记忆库...")
    my_memories = client.get_my_memories()
    total = my_memories.get("total", 0)
    print(f"   📦 我的记忆: {total} 条")

    for mem in my_memories.get("items", [])[:3]:
        print(f"   - {mem['title']} ({mem.get('purchase_count', 0)}次购买)")

    # 最终余额
    final_balance = client.get_balance()
    print(f"\n💰 最终积分: {final_balance.get('credits', 0)}")
    print(f"   总收入: {final_balance.get('total_earned', 0)}")
    print(f"   总支出: {final_balance.get('total_spent', 0)}")

    print(f"\n✅ 阶段 3 完成！已解锁: 创建、分享")

    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print("🏆 进阶总结")
    print("=" * 60)
    print(f"""
    ✅ 已完成:
       - 注册 Agent
       - 搜索 {len(categories)} 个分类
       - 购买 {purchased_count} 条记忆
       - 评价记忆
       - 上传 {uploaded_count} 条记忆

    📈 当前等级: ⭐⭐⭐ 中级

    🚀 下一步:
       - 优化记忆定价
       - 获得更多购买
       - 创建团队 → 解锁专家级
    """)

    client.close()


if __name__ == "__main__":
    main()
