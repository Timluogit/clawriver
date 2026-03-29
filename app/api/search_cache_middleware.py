"""搜索缓存中间件

提供智能搜索结果缓存，显著降低延迟和资源消耗
"""
import asyncio
import logging
import time
from typing import Any, Callable, Optional, Dict, List
from functools import wraps

try:
    from app.cache.redis_client import get_redis_client
except ImportError:
    get_redis_client = None
from app.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class SearchCacheMiddleware:
    """搜索缓存中间件

    功能:
    - 检查缓存
    - 缓存命中返回
    - 缓存未命中执行搜索
    - 异步写入缓存
    """

    def __init__(
        self,
        ttl: int = 3600,  # 1小时
        enabled: bool = True,
        cache_on_miss: bool = True
    ):
        """初始化缓存中间件

        Args:
            ttl: 缓存过期时间（秒）
            enabled: 是否启用缓存
            cache_on_miss: 缓存未命中时是否写入缓存
        """
        self.ttl = ttl
        self.enabled = enabled
        self.cache_on_miss = cache_on_miss
        self.redis = None

    async def initialize(self):
        """初始化Redis客户端"""
        self.redis = await get_redis_client()
        logger.info("Search cache middleware initialized")

    async def search_with_cache(
        self,
        query: str,
        filters: Optional[dict] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None,
        search_func: Optional[Callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """带缓存的搜索

        Args:
            query: 搜索查询
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            sort_by: 排序方式
            search_func: 搜索函数（缓存未命中时调用）
            **kwargs: 其他搜索参数

        Returns:
            {
                "results": list,
                "total": int,
                "cached": bool,
                "cache_key": str,
                "response_time_ms": int
            }
        """
        start_time = time.time()

        # 生成缓存键
        cache_key = CacheKeys.search(
            query=query,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by
        )

        # 如果缓存未启用，直接执行搜索
        if not self.enabled:
            result = await self._execute_search(
                search_func, query, filters, page, page_size, sort_by, **kwargs
            )
            result["cached"] = False
            result["cache_key"] = cache_key
            result["response_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        # 尝试从缓存获取
        cached_result = await self.redis.get(cache_key)
        if cached_result is not None:
            # 缓存命中
            response_time = int((time.time() - start_time) * 1000)

            # 记录统计
            await self._record_hit(cache_key, response_time)

            logger.debug(f"Cache hit for query: {query}")

            return {
                **cached_result,
                "cached": True,
                "cache_key": cache_key,
                "response_time_ms": response_time
            }

        # 缓存未命中
        await self._record_miss(cache_key)
        logger.debug(f"Cache miss for query: {query}")

        # 执行搜索
        result = await self._execute_search(
            search_func, query, filters, page, page_size, sort_by, **kwargs
        )

        response_time = int((time.time() - start_time) * 1000)
        result["cached"] = False
        result["cache_key"] = cache_key
        result["response_time_ms"] = response_time

        # 异步写入缓存
        if self.cache_on_miss and search_func:
            asyncio.create_task(
                self._write_cache(cache_key, result)
            )

        return result

    async def _execute_search(
        self,
        search_func: Callable,
        query: str,
        filters: Optional[dict],
        page: int,
        page_size: int,
        sort_by: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """执行搜索函数"""
        if search_func is None:
            raise ValueError("search_func is required when cache miss")

        # 调用搜索函数
        result = await search_func(
            query=query,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            **kwargs
        )

        return result

    async def _write_cache(self, key: str, value: dict):
        """异步写入缓存"""
        try:
            # 移除不应缓存的数据（如时间戳）
            cache_value = self._prepare_cache_value(value)
            await self.redis.set(key, cache_value, ex=self.ttl)
            logger.debug(f"Cache written: {key}")
        except Exception as e:
            logger.error(f"Failed to write cache: {e}", exc_info=True)

    def _prepare_cache_value(self, value: dict) -> dict:
        """准备缓存值（移除动态字段）"""
        # 复制原始数据
        cache_value = value.copy()

        # 移除不应缓存的字段
        fields_to_remove = [
            "response_time_ms",
            "cached",
            "cache_key",
            "timestamp",
            "request_id"
        ]

        for field in fields_to_remove:
            cache_value.pop(field, None)

        return cache_value

    async def _record_hit(self, key: str, latency_ms: int):
        """记录缓存命中"""
        try:
            # 增加命中计数
            await self.redis.incr(CacheKeys.get_cache_hit_counter())
            # 记录延迟
            # 这里使用Redis的sorted set来记录延迟分布
            # 为简化，暂不实现
        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}")

    async def _record_miss(self, key: str):
        """记录缓存未命中"""
        try:
            # 增加未命中计数
            await self.redis.incr(CacheKeys.get_cache_miss_counter())
        except Exception as e:
            logger.error(f"Failed to record cache miss: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            hits = await self.redis.get(CacheKeys.get_cache_hit_counter())
            misses = await self.redis.get(CacheKeys.get_cache_miss_counter())
            redis_stats = await self.redis.get_stats()

            hits_count = hits if hits is not None else 0
            misses_count = misses if misses is not None else 0
            total_count = hits_count + misses_count

            hit_rate = (hits_count / total_count * 100) if total_count > 0 else 0

            return {
                "hits": hits_count,
                "misses": misses_count,
                "total": total_count,
                "hit_rate": round(hit_rate, 2),
                "redis_stats": redis_stats,
                "ttl": self.ttl,
                "enabled": self.enabled
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    async def clear_cache(self, pattern: Optional[str] = None):
        """清空缓存

        Args:
            pattern: 键模式（如 "search:*"），如果为None则清空所有缓存
        """
        try:
            if pattern:
                count = await self.redis.delete_pattern(pattern)
                logger.info(f"Cleared {count} keys matching pattern: {pattern}")
            else:
                # 清空所有缓存相关的键
                patterns = [
                    f"{CacheKeys.PREFIX_SEARCH}:*",
                    f"{CacheKeys.PREFIX_USER}:*",
                    f"{CacheKeys.PREFIX_TEAM}:*",
                    f"{CacheKeys.PREFIX_MEMORY}:*",
                ]
                total = 0
                for p in patterns:
                    count = await self.redis.delete_pattern(p)
                    total += count
                logger.info(f"Cleared {total} cache keys")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# 全局实例
_search_cache_middleware: Optional[SearchCacheMiddleware] = None


async def get_search_cache_middleware() -> SearchCacheMiddleware:
    """获取搜索缓存中间件实例（单例）

    Returns:
        搜索缓存中间件实例
    """
    global _search_cache_middleware
    if _search_cache_middleware is None:
        _search_cache_middleware = SearchCacheMiddleware()
        await _search_cache_middleware.initialize()
    return _search_cache_middleware


def cache_search(
    ttl: int = 3600,
    enabled: bool = True,
    cache_on_miss: bool = True
):
    """装饰器：为搜索函数添加缓存

    Args:
        ttl: 缓存过期时间（秒）
        enabled: 是否启用缓存
        cache_on_miss: 缓存未命中时是否写入缓存

    Usage:
        @cache_search(ttl=1800)
        async def search_memories(query: str, filters: dict):
            # 搜索逻辑
            return results
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取中间件实例
            middleware = await get_search_cache_middleware()

            # 提取搜索参数
            query = kwargs.get("query")
            filters = kwargs.get("filters")
            page = kwargs.get("page", 1)
            page_size = kwargs.get("page_size", 20)
            sort_by = kwargs.get("sort_by")

            # 执行带缓存的搜索
            result = await middleware.search_with_cache(
                query=query,
                filters=filters,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                search_func=lambda: func(*args, **kwargs),
                **kwargs
            )

            return result

        return wrapper
    return decorator
