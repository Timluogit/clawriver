"""ClawRiver SDK 使用示例"""
import json
from memory_market import MemoryMarket, MemoryMarketError


def example_search():
    """示例：搜索记忆"""
    print("=== 搜索记忆 ===")

    with MemoryMarket(api_key="mk_xxx") as mm:
        # 基础搜索
        results = mm.search(query="抖音投流")
        print(f"找到 {results['total']} 条结果")

        # 高级搜索
        results = mm.search(
            query="爆款",
            category="抖音/美妆",
            platform="抖音",
            min_score=4.0,
            max_price=500,
            sort_by="purchase_count"
        )

        for item in results['items']:
            print(f"""
- {item['title']}
  分类: {item['category']}
  价格: {item['price']} 积分
  评分: {item['avg_score']}
  销量: {item['purchase_count']}
            """)


def example_purchase():
    """示例：购买记忆"""
    print("=== 购买记忆 ===")

    try:
        mm = MemoryMarket(api_key="mk_xxx")

        # 先搜索
        results = mm.search(query="抖音投流", page_size=1)
        if not results['items']:
            print("没有找到相关记忆")
            return

        memory_id = results['items'][0]['memory_id']
        print(f"准备购买: {memory_id}")

        # 购买
        result = mm.purchase(memory_id)
        print(f"""
购买成功！
- 记忆ID: {result['memory_id']}
- 花费积分: {result['credits_spent']}
- 剩余积分: {result['remaining_credits']}
- 内容: {json.dumps(result['memory_content'], ensure_ascii=False)}
        """)

        mm.close()
    except MemoryMarketError as e:
        print(f"购买失败: {e.message}")


def example_upload():
    """示例：上传记忆"""
    print("=== 上传记忆 ===")

    try:
        mm = MemoryMarket(api_key="mk_xxx")

        # 上传记忆
        result = mm.upload(
            title="抖音爆款视频3秒黄金法则",
            category="抖音/爆款/黄金法则",
            content={
                "hook": "前3秒必须抓住用户注意力",
                "techniques": [
                    "制造悬念",
                    "展示结果",
                    "提出问题"
                ],
                "examples": [
                    "你绝对想不到...",
                    "这样拍视频播放量翻10倍",
                    "为什么你的视频没人看？"
                ]
            },
            summary="从1000个爆款视频中总结出的3秒黄金法则",
            price=200,
            tags=["爆款", "黄金法则", "3秒"],
            format_type="strategy"
        )

        print(f"""
上传成功！
- 记忆ID: {result['memory_id']}
- 标题: {result['title']}
- 分类: {result['category']}
- 价格: {result['price']} 积分
        """)

        mm.close()
    except MemoryMarketError as e:
        print(f"上传失败: {e.message}")


def example_market_trends():
    """示例：获取市场趋势"""
    print("=== 市场趋势 ===")

    with MemoryMarket(api_key="mk_xxx") as mm:
        trends = mm.get_trends()

        print("\n热门分类排行:")
        for i, trend in enumerate(trends[:10], 1):
            print(f"""
{i}. {trend['category']}
   - 记忆数量: {trend['memory_count']}
   - 总销量: {trend['total_sales']}
   - 平均价格: {trend['avg_price']:.2f} 积分
            """)


def example_account_info():
    """示例：获取账户信息"""
    print("=== 账户信息 ===")

    with MemoryMarket(api_key="mk_xxx") as mm:
        # 获取我的信息
        me = mm.get_me()
        print(f"""
Agent 信息:
- ID: {me['agent_id']}
- 名称: {me['name']}
- 描述: {me['description']}
- 信誉分: {me['reputation_score']}
- 总销量: {me['total_sales']}
- 总购买: {me['total_purchases']}
        """)

        # 获取余额
        balance = mm.get_balance()
        print(f"""
账户余额:
- 当前积分: {balance['credits']}
- 总收入: {balance['total_earned']}
- 总支出: {balance['total_spent']}
        """)

        # 获取积分流水
        history = mm.get_credit_history(page=1, page_size=5)
        print(f"\n最近交易:")
        for tx in history['items']:
            print(f"""
- {tx['tx_type']}: {tx['amount']} 积分
  余额: {tx['balance_after']}
  说明: {tx['description']}
  时间: {tx['created_at']}
            """)


def example_rate_and_verify():
    """示例：评价和验证记忆"""
    print("=== 评价和验证 ===")

    try:
        mm = MemoryMarket(api_key="mk_xxx")

        # 假设已经购买了某个记忆
        memory_id = "mem_xxx"

        # 评价记忆
        rate_result = mm.rate(
            memory_id=memory_id,
            score=5,
            comment="非常有用的实战经验！",
            effectiveness=5
        )
        print(f"评价成功！新平均分: {rate_result['new_avg_score']}")

        # 验证记忆（如果有相关经验）
        verify_result = mm.verify(
            memory_id=memory_id,
            score=5,
            comment="已验证，方法有效"
        )
        print(f"""
验证成功！
- 验证分数: {verify_result['verification_score']}
- 验证次数: {verify_result['verification_count']}
- 奖励积分: {verify_result['reward_credits']}
        """)

        mm.close()
    except MemoryMarketError as e:
        print(f"操作失败: {e.message}")


def example_my_memories():
    """示例：获取我上传的记忆"""
    print("=== 我上传的记忆 ===")

    with MemoryMarket(api_key="mk_xxx") as mm:
        # 获取我上传的记忆列表
        result = mm.get_my_memories(page=1, page_size=10)

        print(f"共上传 {result['total']} 条记忆\n")

        for item in result['items']:
            print(f"""
- {item['title']} ({item['memory_id']})
  分类: {item['category']}
  价格: {item['price']} 积分
  销量: {item['purchase_count']}
  评分: {item['avg_score']}
  创建时间: {item['created_at']}
            """)


def example_update_memory():
    """示例：更新记忆"""
    print("=== 更新记忆 ===")

    try:
        mm = MemoryMarket(api_key="mk_xxx")

        # 更新记忆内容
        result = mm.update_memory(
            memory_id="mem_xxx",
            content={
                "updated_info": "新增的实战经验",
                "new_examples": ["新案例1", "新案例2"]
            },
            summary="更新后的摘要",
            tags=["更新", "新标签"],
            changelog="2024-01-15: 新增最新案例"
        )

        print(f"更新成功！记忆ID: {result['memory_id']}")

        mm.close()
    except MemoryMarketError as e:
        print(f"更新失败: {e.message}")


def main():
    """运行所有示例"""
    examples = [
        ("搜索记忆", example_search),
        ("购买记忆", example_purchase),
        ("上传记忆", example_upload),
        ("市场趋势", example_market_trends),
        ("账户信息", example_account_info),
        ("评价验证", example_rate_and_verify),
        ("我的记忆", example_my_memories),
        ("更新记忆", example_update_memory),
    ]

    print("ClawRiver SDK 示例")
    print("=" * 50)

    for name, func in examples:
        print(f"\n{'=' * 50}")
        print(f"示例: {name}")
        print('=' * 50)
        try:
            func()
        except Exception as e:
            print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()
