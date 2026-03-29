"""缓存失效服务

提供主动失效和批量失效策略，确保缓存一致性
"""
import asyncio
import logging
from typing import Optional, List, Callable
from datetime import datetime

try:
    from app.cache.redis_client import get_redis_client
except ImportError:
    get_redis_client = None
from app.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class CacheInvalidationService:
    """缓存失效服务

    功能:
    - 记忆更新时失效相关缓存
    - 团队更新时失效相关缓存
    - 批量失效策略
    - 延迟失效（防雪崩）
    """

    def __init__(
        self,
        delay_invalidation: bool = True,
        delay_seconds: int = 5,
        batch_size: int = 100
    ):
        """初始化缓存失效服务

        Args:
            delay_invalidation: 是否启用延迟失效
            delay_seconds: 延迟秒数
            batch_size: 批量失效大小
        """
        self.delay_invalidation = delay_invalidation
        self.delay_seconds = delay_seconds
        self.batch_size = batch_size
        self.redis = None
        self.invalidator_task: Optional[asyncio.Task] = None
        self.invalidation_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

    async def initialize(self):
        """初始化服务"""
        self.redis = await get_redis_client()

        # 启动失效worker
        self.invalidator_task = asyncio.create_task(self._invalidation_worker())
        logger.info("Cache invalidation service initialized")

    async def stop(self):
        """停止服务"""
        if self.invalidator_task:
            self.invalidator_task.cancel()
            try:
                await self.invalidator_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache invalidation service stopped")

    async def _invalidation_worker(self):
        """失效worker（后台任务）"""
        while True:
            try:
                # 从队列获取失效任务
                task = await asyncio.wait_for(
                    self.invalidation_queue.get(),
                    timeout=1.0
                )
                if task is None:
                    break

                # 执行失效
                await self._process_invalidation(task)

                self.invalidation_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Invalidation worker error: {e}", exc_info=True)

    async def _process_invalidation(self, task: dict):
        """处理失效任务"""
        try:
            invalidation_type = task["type"]
            data = task["data"]

            if invalidation_type == "memory":
                await self._invalidate_memory(data)
            elif invalidation_type == "user":
                await self._invalidate_user(data)
            elif invalidation_type == "team":
                await self._invalidate_team(data)
            elif invalidation_type == "pattern":
                await self._invalidate_pattern(data)
            elif invalidation_type == "batch":
                await self._invalidate_batch(data)

        except Exception as e:
            logger.error(f"Failed to process invalidation: {e}", exc_info=True)

    async def invalidate_memory(
        self,
        memory_id: str,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        delay: Optional[bool] = None
    ):
        """失效记忆相关缓存

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（可选）
            team_id: 团队ID（可选）
            delay: 是否延迟失效（默认使用服务配置）
        """
        task = {
            "type": "memory",
            "data": {
                "memory_id": memory_id,
                "user_id": user_id,
                "team_id": team_id
            }
        }

        if delay is None:
            delay = self.delay_invalidation

        if delay:
            # 延迟失效
            asyncio.create_task(
                self._delayed_invalidation(task, self.delay_seconds)
            )
        else:
            # 立即失效
            await self.invalidation_queue.put(task)

    async def invalidate_user(
        self,
        user_id: str,
        delay: Optional[bool] = None
    ):
        """失效用户相关缓存

        Args:
            user_id: 用户ID
            delay: 是否延迟失效
        """
        task = {
            "type": "user",
            "data": {
                "user_id": user_id
            }
        }

        if delay is None:
            delay = self.delay_invalidation

        if delay:
            asyncio.create_task(
                self._delayed_invalidation(task, self.delay_seconds)
            )
        else:
            await self.invalidation_queue.put(task)

    async def invalidate_team(
        self,
        team_id: str,
        delay: Optional[bool] = None
    ):
        """失效团队相关缓存

        Args:
            team_id: 团队ID
            delay: 是否延迟失效
        """
        task = {
            "type": "team",
            "data": {
                "team_id": team_id
            }
        }

        if delay is None:
            delay = self.delay_invalidation

        if delay:
            asyncio.create_task(
                self._delayed_invalidation(task, self.delay_seconds)
            )
        else:
            await self.invalidation_queue.put(task)

    async def invalidate_pattern(
        self,
        pattern: str,
        delay: Optional[bool] = None
    ):
        """失效匹配模式的缓存

        Args:
            pattern: Redis键模式
            delay: 是否延迟失效
        """
        task = {
            "type": "pattern",
            "data": {
                "pattern": pattern
            }
        }

        if delay is None:
            delay = self.delay_invalidation

        if delay:
            asyncio.create_task(
                self._delayed_invalidation(task, self.delay_seconds)
            )
        else:
            await self.invalidation_queue.put(task)

    async def invalidate_batch(
        self,
        memory_ids: List[str],
        user_ids: Optional[List[str]] = None,
        team_ids: Optional[List[str]] = None,
        delay: Optional[bool] = None
    ):
        """批量失效缓存

        Args:
            memory_ids: 记忆ID列表
            user_ids: 用户ID列表（可选）
            team_ids: 团队ID列表（可选）
            delay: 是否延迟失效
        """
        task = {
            "type": "batch",
            "data": {
                "memory_ids": memory_ids,
                "user_ids": user_ids or [],
                "team_ids": team_ids or []
            }
        }

        if delay is None:
            delay = self.delay_invalidation

        if delay:
            asyncio.create_task(
                self._delayed_invalidation(task, self.delay_seconds)
            )
        else:
            await self.invalidation_queue.put(task)

    async def _delayed_invalidation(self, task: dict, delay_seconds: int):
        """延迟失效"""
        try:
            await asyncio.sleep(delay_seconds)
            await self.invalidation_queue.put(task)
            logger.debug(f"Delayed invalidation executed after {delay_seconds}s")
        except Exception as e:
            logger.error(f"Delayed invalidation failed: {e}", exc_info=True)

    async def _invalidate_memory(self, data: dict):
        """失效记忆缓存"""
        memory_id = data["memory_id"]
        user_id = data.get("user_id")
        team_id = data.get("team_id")

        # 获取失效模式
        patterns = CacheKeys.get_invalidation_patterns(
            memory_id=memory_id,
            user_id=user_id,
            team_id=team_id
        )

        # 执行失效
        for pattern in patterns:
            count = await self.redis.delete_pattern(pattern)
            if count > 0:
                logger.info(f"Invalidated {count} keys for memory {memory_id}: {pattern}")

    async def _invalidate_user(self, data: dict):
        """失效用户缓存"""
        user_id = data["user_id"]
        pattern = f"{CacheKeys.PREFIX_USER}:{user_id}:*"
        count = await self.redis.delete_pattern(pattern)
        logger.info(f"Invalidated {count} keys for user {user_id}")

    async def _invalidate_team(self, data: dict):
        """失效团队缓存"""
        team_id = data["team_id"]
        pattern = f"{CacheKeys.PREFIX_TEAM}:{team_id}:*"
        count = await self.redis.delete_pattern(pattern)
        logger.info(f"Invalidated {count} keys for team {team_id}")

    async def _invalidate_pattern(self, data: dict):
        """失效模式匹配的缓存"""
        pattern = data["pattern"]
        count = await self.redis.delete_pattern(pattern)
        logger.info(f"Invalidated {count} keys matching pattern: {pattern}")

    async def _invalidate_batch(self, data: dict):
        """批量失效"""
        memory_ids = data["memory_ids"]
        user_ids = data.get("user_ids", [])
        team_ids = data.get("team_ids", [])

        total_count = 0

        # 失效记忆缓存
        for memory_id in memory_ids[:self.batch_size]:
            patterns = CacheKeys.get_invalidation_patterns(memory_id=memory_id)
            for pattern in patterns:
                count = await self.redis.delete_pattern(pattern)
                total_count += count

        # 失效用户缓存
        for user_id in user_ids[:self.batch_size]:
            pattern = f"{CacheKeys.PREFIX_USER}:{user_id}:*"
            count = await self.redis.delete_pattern(pattern)
            total_count += count

        # 失效团队缓存
        for team_id in team_ids[:self.batch_size]:
            pattern = f"{CacheKeys.PREFIX_TEAM}:{team_id}:*"
            count = await self.redis.delete_pattern(pattern)
            total_count += count

        logger.info(f"Batch invalidated {total_count} keys")


# 全局实例
_cache_invalidation_service: Optional[CacheInvalidationService] = None


async def get_cache_invalidation_service() -> CacheInvalidationService:
    """获取缓存失效服务实例（单例）

    Returns:
        缓存失效服务实例
    """
    global _cache_invalidation_service
    if _cache_invalidation_service is None:
        _cache_invalidation_service = CacheInvalidationService()
        await _cache_invalidation_service.initialize()
    return _cache_invalidation_service
