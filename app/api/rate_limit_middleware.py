"""API Rate Limiting Middleware — 固定窗口 + LRU 淘汰"""
import time
from collections import OrderedDict
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """固定窗口限流中间件（内存安全）"""

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        max_ips: int = 10000,           # 最多跟踪的 IP 数量
        cleanup_interval: int = 1000,   # 每处理 N 个请求做一次清理
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_ips = max_ips
        self.cleanup_interval = cleanup_interval

        # 固定窗口: {ip: {"count": int, "window_start": float}}
        self._windows: OrderedDict[str, dict] = OrderedDict()
        self._total_requests = 0

    def _get_current_window(self, ip: str) -> dict:
        """获取或创建当前窗口"""
        now = time.time()
        window_start = now - (now % self.window_seconds)  # 对齐到固定窗口

        if ip not in self._windows:
            # LRU 淘汰：超过上限时移除最旧的条目
            if len(self._windows) >= self.max_ips:
                self._windows.popitem(last=False)
            self._windows[ip] = {"count": 0, "window_start": window_start}
        else:
            # 将访问的 IP 移到末尾（LRU）
            self._windows.move_to_end(ip)

        entry = self._windows[ip]

        # 窗口过期则重置
        if entry["window_start"] != window_start:
            entry["count"] = 0
            entry["window_start"] = window_start

        return entry

    def _periodic_cleanup(self):
        """定期清理过期窗口"""
        self._total_requests += 1
        if self._total_requests % self.cleanup_interval != 0:
            return

        now = time.time()
        current_window_start = now - (now % self.window_seconds)
        expired = [
            ip for ip, entry in self._windows.items()
            if entry["window_start"] < current_window_start
        ]
        for ip in expired:
            del self._windows[ip]

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        window = self._get_current_window(client_ip)

        if window["count"] >= self.max_requests:
            remaining = self.window_seconds - (time.time() - window["window_start"])
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"请求过于频繁，每分钟最多{self.max_requests}次请求",
                        "data": {"retry_after": max(int(remaining), 1)},
                    },
                },
                headers={"Retry-After": str(max(int(remaining), 1))},
            )

        window["count"] += 1
        self._periodic_cleanup()

        return await call_next(request)
