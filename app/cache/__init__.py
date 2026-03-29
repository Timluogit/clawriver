"""缓存模块"""

try:
    from .redis_client import RedisClient, get_redis_client
    from .cache_keys import CacheKeys
except ImportError:
    RedisClient = None
    get_redis_client = None
    CacheKeys = None

__all__ = [
    "RedisClient",
    "get_redis_client",
    "CacheKeys",
]
