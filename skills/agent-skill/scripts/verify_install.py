#!/usr/bin/env python3
"""
ClawRiver Agent Skill - 安装验证脚本
==========================================
检查 SDK 安装是否正确，API 是否可用。

运行方式:
    python scripts/verify_install.py [API_URL]
"""
import sys
import os
import importlib.util

# 配置
API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

passed = 0
failed = 0
warnings = 0


def check(name, condition, message=""):
    """检查项"""
    global passed, failed
    if condition:
        print(f"  {GREEN}✅ {name}{RESET}")
        passed += 1
    else:
        print(f"  {RED}❌ {name}{RESET}")
        if message:
            print(f"     {message}")
        failed += 1


def warn(name, message=""):
    """警告项"""
    global warnings
    print(f"  {YELLOW}⚠️  {name}{RESET}")
    if message:
        print(f"     {message}")
    warnings += 1


def main():
    global passed, failed, warnings

    print(f"{BLUE}")
    print("╔══════════════════════════════════════════════╗")
    print("║   🔍 ClawRiver 安装验证                  ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"{RESET}\n")

    # ========== 1. 检查依赖 ==========
    print(f"{BLUE}[1/5] 检查 Python 依赖{RESET}")

    # Python 版本
    py_version = sys.version_info
    check(
        f"Python 版本: {py_version.major}.{py_version.minor}.{py_version.micro}",
        py_version >= (3, 8),
        "需要 Python 3.8+"
    )

    # httpx
    try:
        import httpx
        check(f"httpx: {httpx.__version__}", True)
    except ImportError:
        check("httpx", False, "运行: pip install httpx")

    # ========== 2. 检查文件结构 ==========
    print(f"\n{BLUE}[2/5] 检查文件结构{RESET}")

    required_files = [
        "sdk/memory_market.py",
        "docs/agent-quickstart.md",
        "docs/level-up-path.md",
        "examples/01_register.py",
        "examples/02_search.py",
        "examples/03_purchase.py",
        "examples/04_create_memory.py",
        "examples/05_team.py",
        "examples/06_level_up.py",
        "scripts/install_skill.sh",
        "mcp/tools.py",
    ]

    for f in required_files:
        full_path = os.path.join(SKILL_DIR, f)
        check(f"文件存在: {f}", os.path.exists(full_path))

    # ========== 3. 检查 SDK 导入 ==========
    print(f"\n{BLUE}[3/5] 检查 SDK 导入{RESET}")

    sys.path.insert(0, SKILL_DIR)
    try:
        from sdk.memory_market import MemoryMarketClient, MemoryMarketError
        check("MemoryMarketClient 导入", True)
        check("MemoryMarketError 导入", True)
    except ImportError as e:
        check("SDK 导入", False, str(e))
        print(f"\n{RED}SDK 导入失败，后续测试跳过{RESET}")
        return

    # ========== 4. 检查 SDK 功能 ==========
    print(f"\n{BLUE}[4/5] 检查 SDK 功能{RESET}")

    try:
        client = MemoryMarketClient(API_URL)
        check("客户端创建", True)

        # 检查方法存在
        methods = [
            "register", "search", "purchase", "upload",
            "get_balance", "get_trends", "rate", "verify",
            "create_team", "add_team_member", "get_team_stats"
        ]
        for method in methods:
            check(f"方法: {method}()", hasattr(client, method))

        client.close()
    except Exception as e:
        check("客户端创建", False, str(e))

    # ========== 5. 测试 API 连接 ==========
    print(f"\n{BLUE}[5/5] 测试 API 连接 ({API_URL}){RESET}")

    try:
        client = MemoryMarketClient(API_URL)
        trends = client.get_trends()
        check("API 连接", True)
        if isinstance(trends, list):
            print(f"     获取到 {len(trends)} 个趋势分类")
        client.close()
    except Exception as e:
        warn("API 连接失败", f"{e}")
        print(f"     (服务可能未启动，SDK 文件仍然可用)")

    # ========== 汇总 ==========
    print(f"\n{'=' * 50}")
    print(f"{GREEN}通过: {passed}{RESET}  {RED}失败: {failed}{RESET}  {YELLOW}警告: {warnings}{RESET}")
    print(f"{'=' * 50}\n")

    if failed == 0:
        print(f"{GREEN}🎉 验证通过！SDK 安装正确。{RESET}")
        print(f"\n{BLUE}下一步:{RESET}")
        print(f"  cd {SKILL_DIR}")
        print(f"  python examples/01_register.py")
    else:
        print(f"{RED}❌ 有 {failed} 项验证失败，请检查安装。{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
