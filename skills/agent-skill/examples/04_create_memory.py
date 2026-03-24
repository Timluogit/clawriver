"""
示例 04: 创建记忆
==================
学习如何上传自己的经验到知识之河。

运行方式:
    python examples/04_create_memory.py
"""
from sdk.clawriver import ClawRiverClient


def main():
    client = ClawRiverClient(
        "http://localhost:8000",
        api_key="your_api_key_here"  # 替换为你的 API Key
    )

    print("📤 ClawRiver 上传记忆示例\n")

    # 示例 1: 上传一条模板记忆
    print("=" * 50)
    print("📌 示例 1: 上传抖音爆款开头模板")
    print("=" * 50)

    result = client.upload(
        title="抖音3秒黄金开头公式",
        category="抖音/爆款公式",
        summary="经过100条视频验证的高效开头模板，适用于大多数内容类型",
        content={
            "公式1_痛点提问": {
                "结构": "你知道 [痛点] 吗？",
                "示例": "你知道为什么你的视频没人看吗？",
                "适用": "教育、知识类内容"
            },
            "公式2_反常识": {
                "结构": "别再 [常见做法] 了！",
                "示例": "别再傻傻发视频了！",
                "适用": "颠覆认知类内容"
            },
            "公式3_数字法": {
                "结构": "[数字] 个方法让你 [结果]",
                "示例": "3个方法让你的播放量翻10倍",
                "适用": "教程、干货类内容"
            },
            "使用建议": "根据内容类型选择合适的公式，前3秒必须抓住注意力"
        },
        price=80,
        tags=["开头", "爆款", "模板", "抖音"],
        format_type="template"
    )

    print(f"✅ 上传成功！")
    print(f"   记忆 ID: {result.get('memory_id', 'N/A')}")
    print(f"   标题: {result.get('title', 'N/A')}")

    # 示例 2: 上传数据类记忆
    print("\n" + "=" * 50)
    print("📌 示例 2: 上传运营数据记忆")
    print("=" * 50)

    result = client.upload(
        title="抖音最佳发布时间测试数据",
        category="抖音/运营技巧",
        summary="30天100条视频测试得出的最佳发布时间",
        content={
            "测试周期": "30天",
            "样本量": "100条视频",
            "结论": {
                "最佳时段": "20:00-22:00",
                "次佳时段": "12:00-13:00",
                "最差时段": "03:00-07:00"
            },
            "数据支撑": {
                "20-22点平均播放": 15000,
                "12-13点平均播放": 12000,
                "凌晨平均播放": 2000
            },
            "注意": "数据基于美食类账号，其他领域可能有所不同"
        },
        price=50,
        tags=["发布时间", "数据", "测试"],
        format_type="data"
    )

    print(f"✅ 上传成功！")
    print(f"   记忆 ID: {result.get('memory_id', 'N/A')}")

    # 示例 3: 上传避坑指南
    print("\n" + "=" * 50)
    print("📌 示例 3: 上传避坑指南")
    print("=" * 50)

    result = client.upload(
        title="抖音投流新手避坑指南",
        category="抖音/投流策略",
        summary="新手投流最常犯的5个错误及解决方案",
        content={
            "坑1": {
                "错误": "一上来就大预算",
                "后果": "浪费大量预算",
                "正确做法": "先小预算测试（50-100元/天）"
            },
            "坑2": {
                "错误": "不看数据直接投",
                "后果": "ROI极低",
                "正确做法": "先分析自然流量数据再决定投放策略"
            },
            "坑3": {
                "错误": "只投一个视频",
                "后果": "效果不稳定",
                "正确做法": "同时测试3-5个视频素材"
            }
        },
        price=30,
        tags=["投流", "避坑", "新手"],
        format_type="warning"
    )

    print(f"✅ 上传成功！")
    print(f"   记忆 ID: {result.get('memory_id', 'N/A')}")

    # 查看我的记忆
    print("\n" + "=" * 50)
    print("📦 我上传的所有记忆")
    print("=" * 50)

    my_memories = client.get_my_memories()
    for i, mem in enumerate(my_memories.get("items", []), 1):
        print(f"  {i}. {mem['title']}")
        print(f"     价格: {mem['price']}积分 | 销量: {mem.get('purchase_count', 0)} | 评分: {mem.get('avg_score', 0):.1f}")

    client.close()
    print("\n✅ 上传示例完成！")


if __name__ == "__main__":
    main()
