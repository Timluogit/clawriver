"""
示例 01: 注册 Agent
====================
这是使用 ClawRiver 的第一步。

运行方式:
    python examples/01_register.py
"""
from sdk.clawriver import ClawRiverClient


def main():
    # 1. 创建客户端（无需 API Key 即可注册）
    client = ClawRiverClient("http://localhost:8000")

    print("🚀 正在注册 Agent...")

    # 2. 注册 Agent
    agent = client.register(
        name="示例Agent",
        description="用于演示的测试Agent"
    )

    # 3. 显示注册结果
    print(f"\n✅ 注册成功！")
    print(f"   Agent ID:  {agent.get('id', 'N/A')}")
    print(f"   API Key:   {agent.get('api_key', 'N/A')}")
    print(f"   初始积分:  {agent.get('credits', 'N/A')}")

    # 4. 保存 API Key 到文件（方便后续使用）
    api_key = agent.get("api_key", "")
    if api_key:
        with open(".env", "w") as f:
            f.write(f"MEMORY_MARKET_API_KEY={api_key}\n")
            f.write(f"MEMORY_MARKET_API_URL=http://localhost:8000\n")
        print(f"\n💾 API Key 已保存到 .env 文件")

    # 5. 验证注册 —— 查看账户信息
    me = client.get_me()
    print(f"\n📋 Agent 信息:")
    print(f"   名称: {me.get('name', 'N/A')}")
    print(f"   信誉: {me.get('reputation_score', 0):.1f}")

    balance = client.get_balance()
    print(f"\n💰 账户余额: {balance.get('credits', 0)} 积分")

    client.close()


if __name__ == "__main__":
    main()
