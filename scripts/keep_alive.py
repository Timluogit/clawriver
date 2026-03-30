#!/usr/bin/env python3
"""
ClawRiver Keep-Alive Script

用于防止 Render 免费版应用休眠，每 10 分钟 ping 一次健康检查端点。
支持两种运行模式：
1. 单次执行模式：python scripts/keep_alive.py
2. 守护进程模式：python scripts/keep_alive.py --daemon
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  requests 库未安装，使用 urllib")
    import urllib.request
    import urllib.error


# 默认配置
DEFAULT_URL = "https://clawriver.onrender.com/health"
DEFAULT_INTERVAL = 600  # 10 分钟，单位秒
DEFAULT_TIMEOUT = 10  # 10 秒超时


def ping_health_check(url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """
    Ping 健康检查端点

    Args:
        url: 健康检查 URL
        timeout: 超时时间（秒）

    Returns:
        bool: 是否成功
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if HAS_REQUESTS:
            response = requests.get(url, timeout=timeout)
            success = response.status_code == 200
            status = f"OK ({response.status_code})" if success else f"FAIL ({response.status_code})"
        else:
            # 使用 urllib 作为备用
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                success = response.status == 200
                status = f"OK ({response.status})" if success else f"FAIL ({response.status})"

        print(f"[{timestamp}] {status} - {url}")
        return success

    except Exception as e:
        print(f"[{timestamp}] ERROR - {str(e)}")
        return False


def run_daemon(url: str, interval: int, timeout: int):
    """
    以守护进程模式运行

    Args:
        url: 健康检查 URL
        interval: 间隔时间（秒）
        timeout: 超时时间（秒）
    """
    print(f"🚀 ClawRiver Keep-Alive 守护进程启动")
    print(f"   URL: {url}")
    print(f"   间隔: {interval} 秒 ({interval // 60} 分钟)")
    print(f"   超时: {timeout} 秒")
    print(f"   按 Ctrl+C 停止\n")

    try:
        while True:
            ping_health_check(url, timeout)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 Keep-Alive 守护进程已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ClawRiver Keep-Alive 脚本 - 防止 Render 免费版应用休眠",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单次 ping
  python scripts/keep_alive.py
  
  # 单次 ping 自定义 URL
  python scripts/keep_alive.py --url https://my-app.onrender.com/health
  
  # 守护进程模式（持续运行）
  python scripts/keep_alive.py --daemon
  
  # 守护进程模式，5 分钟间隔
  python scripts/keep_alive.py --daemon --interval 300
        """
    )

    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("KEEP_ALIVE_URL", DEFAULT_URL),
        help=f"健康检查 URL (默认: {DEFAULT_URL})"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("KEEP_ALIVE_INTERVAL", str(DEFAULT_INTERVAL))),
        help=f"ping 间隔（秒）(默认: {DEFAULT_INTERVAL}秒 = 10分钟)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("KEEP_ALIVE_TIMEOUT", str(DEFAULT_TIMEOUT))),
        help=f"请求超时（秒）(默认: {DEFAULT_TIMEOUT}秒)"
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="以守护进程模式持续运行"
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.url, args.interval, args.timeout)
    else:
        # 单次执行模式
        success = ping_health_check(args.url, args.timeout)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
