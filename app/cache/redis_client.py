"""Redis客户端封装

提供连接池管理、健康检查、序列化/反序列化等功能
"""
import json
import logging
import pickle
from typing import Any, Optional
from contextlib import asynccontextmanager

from app.core.config import settings

try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端

    支持同步和异步操作，提供连接池管理和健康检查
    """

    def __init__(
        self,
        url: Optional[str] = None,
        max_connections: int = 50,
        decode_responses: bool = False
    ):
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package not installed")
        """初始化Redis客户端

        Args:
            url: Redis连接URL
            max_connections: 最大连接数
            decode_responses: 是否自动解码响应
        """
        self.url = url or getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self._pool: Optional[ConnectionPool] = None

    async def connect(self):
        """创建连接池"""
        try:
            self._pool = ConnectionPool.from_url(
                self.url,
                max_connections=self.max_connections,
                decode_responses=self.decode_responses,
                socket_connect_timeout=3,   # 3秒连接超时，防止无Redis时卡住
                socket_timeout=3,           # 3秒读写超时
                retry_on_timeout=False,
            )
            logger.info(f"Redis connected: {self.url}")
            return self
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis disconnected")

    @asynccontextmanager
    async def get_client(self):
        """获取Redis客户端（上下文管理器）"""
        if not self._pool:
            await self.connect()

        client = redis.Redis(connection_pool=self._pool)
        try:
            yield client
        finally:
            await client.close()

    async def ping(self) -> bool:
        """健康检查"""
        try:
            async with self.get_client() as client:
                return await client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """获取值（自动反序列化）"""
        try:
            async with self.get_client() as client:
                value = await client.get(key)
                if value is None:
                    return None
                return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None
    ) -> bool:
        """设置值（自动序列化）

        Args:
            key: 键
            value: 值
            ex: 过期时间（秒）
            px: 过期时间（毫秒）

        Returns:
            是否成功
        """
        try:
            serialized = self._serialize(value)
            async with self.get_client() as client:
                return await client.set(key, serialized, ex=ex, px=px)
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除键"""
        try:
            async with self.get_client() as client:
                return await client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """批量删除匹配的键

        Args:
            pattern: 键模式（如 "search:*"）

        Returns:
            删除的键数量
        """
        try:
            async with self.get_client() as client:
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    return await client.delete(*keys)
                return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern failed for pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            async with self.get_client() as client:
                return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists failed for key {key}: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            async with self.get_client() as client:
                return await client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间（秒）"""
        try:
            async with self.get_client() as client:
                return await client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl failed for key {key}: {e}")
            return -1

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        try:
            async with self.get_client() as client:
                return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr failed for key {key}: {e}")
            return None

    async def get_stats(self) -> dict:
        """获取Redis统计信息

        Returns:
            {
                "used_memory": int,
                "used_memory_human": str,
                "connected_clients": int,
                "total_connections_received": int,
                "total_commands_processed": int,
                "keyspace_hits": int,
                "keyspace_misses": int
            }
        """
        try:
            async with self.get_client() as client:
                info = await client.info()
                stats = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_connections_received": info.get("total_connections_received", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
                return stats
        except Exception as e:
            logger.error(f"Redis get_stats failed: {e}")
            return {}

    def _serialize(self, value: Any) -> bytes:
        """序列化值

        优先使用JSON，失败则使用pickle
        """
        try:
            return json.dumps(value).encode("utf-8")
        except (TypeError, ValueError):
            try:
                return pickle.dumps(value)
            except Exception as e:
                logger.error(f"Failed to serialize value: {e}")
                raise

    def _deserialize(self, value: bytes) -> Any:
        """反序列化值

        优先尝试JSON，失败则尝试pickle
        """
        try:
            return json.loads(value.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                return pickle.loads(value)
            except Exception as e:
                logger.error(f"Failed to deserialize value: {e}")
                raise

    async def close(self):
        """关闭连接（兼容旧接口）"""
        await self.disconnect()


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """获取Redis客户端实例（单例）

    Returns:
        Redis客户端实例
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


async def close_redis_client():
    """关闭Redis客户端"""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None
