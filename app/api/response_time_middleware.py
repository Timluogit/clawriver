"""
响应时间记录中间件

为 API 响应添加 X-Response-Time 头部，用于监控性能
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """
    响应时间中间件
    
    记录请求处理时间并添加到响应头部
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录响应时间
        
        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            FastAPI 响应对象
        """
        start_time = time.perf_counter()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算响应时间
        process_time = time.perf_counter() - start_time
        
        # 添加响应时间头部
        response.headers["X-Response-Time"] = f"{process_time:.6f}"
        
        return response


def add_response_time_header(response: Response, start_time: float) -> None:
    """
    手动为响应添加响应时间头部
    
    用于在特定路由中单独记录更精确的响应时间
    
    Args:
        response: FastAPI 响应对象
        start_time: 开始时间（使用 time.perf_counter() 获取）
    """
    process_time = time.perf_counter() - start_time
    response.headers["X-Response-Time"] = f"{process_time:.6f}"
