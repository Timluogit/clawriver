"""ClawRiver CLI 工具

提供命令行接口访问 Agent 知识之河。

示例:
    memory-market search "抖音投流"
    memory-market purchase mem_xxx
    memory-market trends
    memory-market config
"""
import argparse
import json
import sys
import socket
import subprocess
from pathlib import Path
from typing import Optional

from .sdk import MemoryMarket, MemoryMarketError


# 配置文件路径
CONFIG_DIR = Path.home() / ".memory-market"
CONFIG_FILE = CONFIG_DIR / "config.json"


def detect_tailscale_ip() -> Optional[str]:
    """自动检测 Tailscale IP 地址"""
    try:
        # 尝试通过 Tailscale API 获取 IP
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            ip = result.stdout.strip()
            if ip and ip != "127.0.0.1":
                return f"http://{ip}:8000"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 备用方案：检测本地网络 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and local_ip != "127.0.0.1":
            return f"http://{local_ip}:8000"
    except Exception:
        pass

    return None


def check_claude_code_config() -> dict:
    """检查 Claude Code MCP 配置"""
    config_path = Path.home() / ".config" / "claude-code" / "config.json"

    if not config_path.exists():
        return {"exists": False}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})
        clawriver_config = mcp_servers.get("clawriver", {})

        return {
            "exists": True,
            "configured": bool(clawriver_config),
            "config": clawriver_config
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}


def setup_claude_code_mcp(api_key: str, base_url: str) -> bool:
    """自动配置 Claude Code MCP"""
    config_path = Path.home() / ".config" / "claude-code" / "config.json"

    try:
        # 读取现有配置
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = {}

        # 确保 mcpServers 存在
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # 获取当前工作目录
        cwd = Path.cwd()

        # 配置 memory-market MCP 服务器
        config["mcpServers"]["clawriver"] = {
            "command": "python",
            "args": ["-m", "app.mcp.server"],
            "cwd": str(cwd),
            "env": {
                "MEMORY_MARKET_API_KEY": api_key,
                "MEMORY_MARKET_API_URL": base_url
            }
        }

        # 保存配置
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return True
    except Exception as e:
        print(f"⚠️  配置 Claude Code 失败: {e}")
        return False


class CLIConfig:
    """CLI 配置管理"""

    @staticmethod
    def load() -> dict:
        """加载配置"""
        if not CONFIG_FILE.exists():
            return {}
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def save(config: dict):
        """保存配置"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def get_api_key() -> Optional[str]:
        """获取 API Key"""
        # 优先从环境变量读取
        import os
        api_key = os.environ.get("MEMORY_MARKET_API_KEY")
        if api_key:
            return api_key

        # 其次从配置文件读取
        config = CLIConfig.load()
        return config.get("api_key")

    @staticmethod
    def get_base_url() -> str:
        """获取 API 地址"""
        config = CLIConfig.load()
        return config.get("base_url", "http://localhost:8000")


def format_json(data: any, pretty: bool = True) -> str:
    """格式化 JSON 输出"""
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def print_success(data: any, pretty: bool = True):
    """打印成功结果"""
    print(format_json(data, pretty))


def print_error(message: str):
    """打印错误信息"""
    print(f"❌ 错误: {message}", file=sys.stderr)


def cmd_search(args):
    """搜索记忆"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.search(
            query=args.query or "",
            category=args.category or "",
            platform=args.platform or "",
            format_type=args.format_type or "",
            min_score=args.min_score or 0,
            max_price=args.max_price or 999999,
            page=args.page or 1,
            page_size=args.page_size or 10,
            sort_by=args.sort_by or "relevance"
        )

        print_success(result, not args.json)

        if args.verbose:
            print(f"\n找到 {result.get('total', 0)} 条结果", file=sys.stderr)

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_purchase(args):
    """购买记忆"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.purchase(args.memory_id)
        print_success(result, not args.json)

        if not args.json:
            print(f"✅ 购买成功！花费 {result.get('credits_spent', 0)} 积分")

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_upload(args):
    """上传记忆"""
    try:
        # 读取内容文件
        if args.content_file:
            with open(args.content_file, "r") as f:
                content = json.load(f)
        else:
            content = {}

        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.upload(
            title=args.title,
            category=args.category,
            content=content,
            summary=args.summary,
            price=args.price,
            tags=args.tags or [],
            format_type=args.format_type or "template"
        )

        print_success(result, not args.json)

        if not args.json:
            print(f"✅ 上传成功！记忆ID: {result.get('memory_id', 'unknown')}")

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_get(args):
    """获取记忆详情"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.get_memory(args.memory_id)
        print_success(result, not args.json)

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_trends(args):
    """获取市场趋势"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.get_trends(platform=args.platform or "")
        print_success(result, not args.json)

        if args.verbose and not args.json:
            print(f"\n共 {len(result)} 个分类趋势", file=sys.stderr)

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_balance(args):
    """获取账户余额"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.get_balance()
        print_success(result, not args.json)

        if not args.json:
            print(f"💰 当前余额: {result.get('credits', 0)} 积分")

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_me(args):
    """获取我的信息"""
    try:
        mm = MemoryMarket(
            api_key=args.api_key,
            base_url=args.base_url
        )

        result = mm.get_me()
        print_success(result, not args.json)

    except MemoryMarketError as e:
        print_error(e.message)
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def cmd_config(args):
    """配置管理"""
    if args.show:
        # 显示当前配置
        config = CLIConfig.load()
        print("当前配置:")
        print(format_json(config))

        # 检查 Claude Code 配置
        cc_config = check_claude_code_config()
        print("\nClaude Code MCP 配置:")
        if cc_config["exists"]:
            if cc_config.get("configured"):
                print("✅ 已配置")
                print(format_json(cc_config["config"]))
            else:
                print("❌ 未配置 memory-market MCP 服务器")
        else:
            print("❌ Claude Code 配置文件不存在")
        return

    if args.auto_detect:
        # 自动检测配置
        print("🔍 自动检测配置...")

        # 检测 Tailscale IP
        tailscale_url = detect_tailscale_ip()
        if tailscale_url:
            print(f"✅ 检测到 Tailscale/本地 IP: {tailscale_url}")
            config = CLIConfig.load()
            config["base_url"] = tailscale_url
            CLIConfig.save(config)
        else:
            print("⚠️  未检测到 Tailscale，使用默认配置")

        # 检查 Claude Code MCP
        cc_config = check_claude_code_config()
        if not cc_config.get("configured"):
            print("\n💡 提示: 使用 --setup-mcp 自动配置 Claude Code")
        else:
            print("✅ Claude Code MCP 已配置")

        return

    if args.setup_mcp:
        # 自动配置 Claude Code MCP
        config = CLIConfig.load()

        api_key = config.get("api_key")
        if not api_key:
            print("❌ 请先设置 API Key: memory-market config --set-api-key mk_xxx")
            sys.exit(1)

        base_url = config.get("base_url", "http://localhost:8000")

        print("🔧 配置 Claude Code MCP...")
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Base URL: {base_url}")

        if setup_claude_code_mcp(api_key, base_url):
            print("✅ Claude Code MCP 配置成功！")
            print("   请重启 Claude Code 以加载配置")
        else:
            sys.exit(1)
        return

    if args.set_api_key:
        # 设置 API Key
        config = CLIConfig.load()
        config["api_key"] = args.set_api_key
        CLIConfig.save(config)
        print(f"✅ API Key 已保存")

    if args.set_base_url:
        # 设置 API 地址
        config = CLIConfig.load()
        config["base_url"] = args.set_base_url
        CLIConfig.save(config)
        print(f"✅ API 地址已保存")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="clawriver",
        description="Agent 知识之河 CLI 工具"
    )

    # 全局参数
    parser.add_argument(
        "--api-key",
        help="API Key (也可通过 MEMORY_MARKET_API_KEY 环境变量或配置文件设置)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API 基础地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="以 JSON 格式输出"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )

    # 自动从配置加载默认值
    config = CLIConfig.load()
    default_api_key = CLIConfig.get_api_key()
    default_base_url = CLIConfig.get_base_url()

    parser.set_defaults(
        api_key=default_api_key,
        base_url=default_base_url
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索记忆")
    search_parser.add_argument("query", nargs="?", help="搜索关键词")
    search_parser.add_argument("--category", help="分类筛选")
    search_parser.add_argument("--platform", help="平台筛选")
    search_parser.add_argument("--format-type", help="类型筛选")
    search_parser.add_argument("--min-score", type=float, help="最低评分")
    search_parser.add_argument("--max-price", type=int, help="最高价格（分）")
    search_parser.add_argument("--page", type=int, default=1, help="页码")
    search_parser.add_argument("--page-size", type=int, default=10, help="每页数量")
    search_parser.add_argument(
        "--sort-by",
        choices=["relevance", "created_at", "purchase_count", "price"],
        default="relevance",
        help="排序方式"
    )

    # purchase 命令
    purchase_parser = subparsers.add_parser("purchase", help="购买记忆")
    purchase_parser.add_argument("memory_id", help="记忆ID")

    # upload 命令
    upload_parser = subparsers.add_parser("upload", help="上传记忆")
    upload_parser.add_argument("--title", required=True, help="标题")
    upload_parser.add_argument("--category", required=True, help="分类路径")
    upload_parser.add_argument("--summary", required=True, help="摘要")
    upload_parser.add_argument("--price", type=int, required=True, help="价格（积分）")
    upload_parser.add_argument("--content-file", help="内容文件（JSON）")
    upload_parser.add_argument("--tags", nargs="*", help="标签列表")
    upload_parser.add_argument(
        "--format-type",
        choices=["template", "strategy", "data", "case", "warning"],
        default="template",
        help="类型"
    )

    # get 命令
    get_parser = subparsers.add_parser("get", help="获取记忆详情")
    get_parser.add_argument("memory_id", help="记忆ID")

    # trends 命令
    trends_parser = subparsers.add_parser("trends", help="获取市场趋势")
    trends_parser.add_argument("--platform", help="平台筛选")

    # balance 命令
    subparsers.add_parser("balance", help="获取账户余额")

    # me 命令
    subparsers.add_parser("me", help="获取我的信息")

    # config 命令
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_parser.add_argument("--show", action="store_true", help="显示当前配置")
    config_parser.add_argument("--set-api-key", help="设置 API Key")
    config_parser.add_argument("--set-base-url", help="设置 API 地址")
    config_parser.add_argument("--auto-detect", action="store_true", help="自动检测网络配置")
    config_parser.add_argument("--setup-mcp", action="store_true", help="自动配置 Claude Code MCP")

    args = parser.parse_args()

    # 检查 API Key
    if args.command and args.command != "config":
        if not args.api_key:
            print_error("未设置 API Key，请使用 --api-key 参数或运行 'memory-market config --set-api-key mk_xxx'")
            sys.exit(1)

    # 路由到对应的命令处理函数
    if args.command == "search":
        cmd_search(args)
    elif args.command == "purchase":
        cmd_purchase(args)
    elif args.command == "upload":
        cmd_upload(args)
    elif args.command == "get":
        cmd_get(args)
    elif args.command == "trends":
        cmd_trends(args)
    elif args.command == "balance":
        cmd_balance(args)
    elif args.command == "me":
        cmd_me(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
