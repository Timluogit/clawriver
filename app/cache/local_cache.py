"""本地内存缓存 — Redis 不可用时的后备方案"""
import time
import threading
from typing import Any, Optional
from collections import OrderedDict


class LocalCache:
    """线程安全的 LRU 本地内存缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_size = max_size
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)  # LRU
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # 淘汰最旧
            self._cache[key] = (value, time.time() + (ttl or self.default_ttl))

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """简易模式匹配删除"""
        import fnmatch
        with self._lock:
            keys_to_delete = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)

    def clear(self):
        with self._lock:
            self._cache.clear()


# 全局单例
local_cache = LocalCache(max_size=2000, default_ttl=300)
