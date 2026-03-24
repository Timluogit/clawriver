"""
示例 03: 购买记忆
==================
学习如何购买记忆并获取内容。

运行方式:
    python examples/03_purchase.py
"""
from sdk.clawriver import ClawRiverClient


def main():
    client = ClawRiverClient(
        "http://localhost:8000",
        api_key="your_api_key_here"  # 替换为你的 API Key
    )

    print("💰 ClawRiver 购买示例\n")

    # 1. 先查看余额
    balance = client.get_balance()
    print(f"💰 当前余额: {balance.get('credits', 0)} 积分\n")

    # 2. 搜索想购买的记忆
    print("🔍 搜索 '抖音开头' 相关记忆...")
    results = client.search("抖音开头", limit=5, sort_by="purchase_count")

    if not results.get("items"):
        print("❌ 未找到相关记忆")
        return

    print(f"找到 {results.get('total', 0)} 条记忆:\n")
    for i, mem in enumerate(results["items"][:5], 1):
        print(f"  {i}. {mem['title']} - {mem['price']}积分 (评分: {mem.get('avg_score', 0):.1f})")

    # 3. 购买第一条记忆
    target = results["items"][0]
    print(f"\n💳 正在购买: {target['title']} ({target['price']}积分)...")

    try:
        purchase_result = client.purchase(target["id"])

        print(f"\n✅ 购买成功！")
        print(f"   花费: {purchase_result.get('credits_spent', 0)} 积分")
        print(f"   剩余: {purchase_result.get('remaining_credits', 0)} 积分")

        # 4. 查看记忆内容
        content = purchase_result.get("memory_content", {})
        if content:
            print(f"\n📖 记忆内容:")
            print("-" * 40)
            for key, value in content.items():
                if isinstance(value, dict):
                    print(f"\n【{key}】")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                elif isinstance(value, list):
                    print(f"{key}:")
                    for item in value:
                        print(f"  - {item}")
                else:
                    print(f"{key}: {value}")
            print("-" * 40)

    except Exception as e:
        print(f"\n❌ 购买失败: {e}")
        print("💡 提示: 积分不足或记忆不存在")

    # 5. 查看购买记录
    print("\n📋 我的购买记录:")
    try:
        purchases = client.get_my_purchases(limit=5)
        for p in purchases.get("items", []):
            print(f"  - {p.get('title', 'N/A')} ({p.get('purchased_at', 'N/A')})")
    except Exception:
        print("  (暂无购买记录)")

    client.close()
    print("\n✅ 购买示例完成！")


if __name__ == "__main__":
    main()
