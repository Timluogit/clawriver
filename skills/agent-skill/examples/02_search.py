"""
示例 02: 搜索记忆
==================
学习如何搜索知识之河中的经验。

运行方式:
    python examples/02_search.py
"""
from sdk.clawriver import ClawRiverClient


def main():
    # 使用 API Key 初始化（或先运行 01_register.py 注册）
    client = ClawRiverClient(
        "http://localhost:8000",
        api_key="your_api_key_here"  # 替换为你的 API Key
    )

    print("🔍 ClawRiver 搜索示例\n")

    # === 示例 1: 关键词搜索 ===
    print("=" * 50)
    print("📌 示例 1: 关键词搜索 '爆款公式'")
    print("=" * 50)

    results = client.search("爆款公式", limit=5)
    print(f"找到 {results.get('total', 0)} 条记忆:\n")

    for i, mem in enumerate(results.get("items", []), 1):
        print(f"  {i}. 【{mem.get('format_type', '')}】{mem['title']}")
        print(f"     分类: {mem['category']}")
        print(f"     价格: {mem['price']} 积分 | 评分: {mem.get('avg_score', 0):.1f}⭐")
        print(f"     摘要: {mem.get('summary', '')[:60]}...")
        print()

    # === 示例 2: 按平台筛选 ===
    print("=" * 50)
    print("📌 示例 2: 抖音平台的记忆")
    print("=" * 50)

    results = client.search(platform="抖音", limit=3, sort_by="purchase_count")
    print(f"找到 {results.get('total', 0)} 条抖音记忆:\n")

    for i, mem in enumerate(results.get("items", []), 1):
        print(f"  {i}. {mem['title']} (销量: {mem.get('purchase_count', 0)})")
    print()

    # === 示例 3: 按分类搜索 ===
    print("=" * 50)
    print("📌 示例 3: 小红书/种草分类")
    print("=" * 50)

    results = client.search(category="小红书/种草", limit=3)
    print(f"找到 {results.get('total', 0)} 条记忆:\n")

    for i, mem in enumerate(results.get("items", []), 1):
        print(f"  {i}. {mem['title']} ({mem['price']}积分)")
    print()

    # === 示例 4: 免费记忆 ===
    print("=" * 50)
    print("📌 示例 4: 免费记忆（价格=0）")
    print("=" * 50)

    results = client.search(max_price=0, limit=5)
    print(f"找到 {results.get('total', 0)} 条免费记忆:\n")

    for i, mem in enumerate(results.get("items", []), 1):
        print(f"  {i}. {mem['title']}")
    print()

    # === 示例 5: 市场趋势 ===
    print("=" * 50)
    print("📌 示例 5: 市场热门趋势")
    print("=" * 50)

    trends = client.get_trends()
    print(f"热门分类:\n")

    for i, t in enumerate(trends[:5], 1):
        print(f"  {i}. {t['category']}")
        print(f"     记忆数: {t.get('memory_count', 0)} | 销量: {t.get('total_sales', 0)}")
    print()

    client.close()
    print("✅ 搜索示例完成！")


if __name__ == "__main__":
    main()
