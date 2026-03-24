"""重排序服务 - 使用 Cross-Encoder 对搜索结果进行精细排序

注意：sentence_transformers / numpy 均为懒加载，
仅在实际调用 CrossEncoder 重排时才导入，避免启动时占用大量内存。
当 sentence_transformers 未安装时，重排功能自动禁用，降级为原始排序。
"""
import math
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.model_manager import get_model_manager
from app.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RerankingService:
    """重排序服务

    功能:
    1. Batch 重排序（支持多候选）
    2. 评分计算（相似度分数）
    3. Top-K 筛选
    4. 缓存优化（结果缓存）
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-large",
        top_k: int = 20,
        threshold: float = 0.5,
        cache_ttl: int = 3600  # 1小时
    ):
        """初始化重排序服务

        Args:
            model_name: CrossEncoder 模型名称
            top_k: 重排后保留的Top-K数量
            threshold: 最低相关性阈值（低于此值的会被过滤）
            cache_ttl: 缓存过期时间（秒）
        """
        self.model_name = model_name
        self.top_k = top_k
        self.threshold = threshold
        self.cache_ttl = cache_ttl

        # 获取模型管理器
        self.model_manager = get_model_manager()

        # CrossEncoder 模型（延迟加载）
        self._encoder: Optional[CrossEncoder] = None

        # Redis 缓存
        self._redis = None

    @property
    def encoder(self) -> CrossEncoder:
        """获取 CrossEncoder 模型（延迟加载）"""
        if self._encoder is None:
            logger.info(f"Loading CrossEncoder: {self.model_name}")
            self._encoder = self.model_manager.get_cross_encoder(self.model_name)
            logger.info("CrossEncoder loaded successfully")
        return self._encoder

    @property
    def redis(self):
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    def _get_cache_key(self, query: str, memory_ids: List[str]) -> str:
        """生成缓存键

        Args:
            query: 搜索查询
            memory_ids: 记忆ID列表

        Returns:
            缓存键
        """
        import hashlib
        content = f"{query}:{','.join(sorted(memory_ids))}"
        return f"rerank:{hashlib.md5(content.encode()).hexdigest()}"

    async def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """对候选结果进行重排序

        Args:
            query: 搜索查询
            candidates: 候选结果列表，每个元素需包含 memory_id 和 text/content 字段
            top_k: 重排后保留的数量（默认使用初始化参数）
            threshold: 最低相关性阈值（默认使用初始化参数）
            use_cache: 是否使用缓存

        Returns:
            重排序后的结果列表，按相关性降序排列
        """
        if not candidates:
            return []

        # 使用默认参数
        top_k = top_k or self.top_k
        threshold = threshold or self.threshold

        # 如果候选数量 <= top_k，直接返回（无需重排）
        if len(candidates) <= top_k:
            logger.debug(f"Candidates ({len(candidates)}) <= top_k ({top_k}), skipping rerank")
            return candidates

        # 尝试从缓存获取
        if use_cache:
            try:
                cached = await self._get_from_cache(query, candidates, top_k, threshold)
                if cached is not None:
                    logger.debug("Rerank result from cache")
                    return cached
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # 提取文本
        memory_ids = []
        texts = []
        texts_map = {}  # 映射文本到原始候选

        for i, cand in enumerate(candidates):
            memory_id = cand.get('memory_id')
            # 优先使用 content，其次 summary
            text = cand.get('content') or cand.get('summary', '')
            if not text:
                logger.warning(f"No text for memory {memory_id}, using title")
                text = cand.get('title', '')

            memory_ids.append(memory_id)
            texts.append(text)
            texts_map[text] = cand

        # 准备输入：[query, text1], [query, text2], ...
        pairs = [[query, text] for text in texts]

        # 批量计算分数
        logger.debug(f"Reranking {len(pairs)} pairs with {self.model_name}")
        try:
            scores = self.encoder.predict(pairs, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Rerank prediction failed: {e}")
            # 失败时返回原始结果
            return candidates[:top_k]

        # 创建带分数的结果
        scored_results = []
        for i, (memory_id, score) in enumerate(zip(memory_ids, scores)):
            # 过滤低分结果
            if score < threshold:
                logger.debug(f"Memory {memory_id} score {score:.3f} below threshold {threshold}, skipped")
                continue

            # 添加分数到原始候选
            result = texts_map[texts[i]].copy()
            result['rerank_score'] = float(score)
            scored_results.append(result)

        # 按分数降序排序
        scored_results.sort(key=lambda x: x['rerank_score'], reverse=True)

        # 取 Top-K
        reranked = scored_results[:top_k]

        logger.info(f"Reranked: {len(candidates)} -> {len(reranked)} candidates (threshold={threshold})")

        # 缓存结果
        if use_cache:
            try:
                await self._save_to_cache(query, candidates, reranked, top_k, threshold)
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return reranked

    async def _get_from_cache(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int,
        threshold: float
    ) -> Optional[List[Dict]]:
        """从缓存获取重排结果

        Args:
            query: 搜索查询
            candidates: 原始候选结果
            top_k: Top-K 数量
            threshold: 阈值

        Returns:
            缓存的结果，如果不存在返回 None
        """
        cache_key = self._get_cache_key(query, [c.get('memory_id') for c in candidates])

        if not settings.CACHE_ENABLED:
            return None

        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                import json
                cached = json.loads(cached_data)

                # 检查参数是否匹配
                if (cached.get('top_k') == top_k and
                    cached.get('threshold') == threshold and
                    cached.get('model') == self.model_name):
                    # 返回缓存的memory_id列表，并从原始候选中恢复完整数据
                    reranked_ids = cached.get('reranked_ids', [])
                    id_to_candidate = {c.get('memory_id'): c for c in candidates}
                    return [id_to_candidate[mid] for mid in reranked_ids if mid in id_to_candidate]
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _save_to_cache(
        self,
        query: str,
        candidates: List[Dict],
        reranked: List[Dict],
        top_k: int,
        threshold: float
    ):
        """保存重排结果到缓存

        Args:
            query: 搜索查询
            candidates: 原始候选结果
            reranked: 重排后的结果
            top_k: Top-K 数量
            threshold: 阈值
        """
        if not settings.CACHE_ENABLED:
            return

        cache_key = self._get_cache_key(query, [c.get('memory_id') for c in candidates])

        try:
            import json
            cached_data = {
                'reranked_ids': [r.get('memory_id') for r in reranked],
                'top_k': top_k,
                'threshold': threshold,
                'model': self.model_name,
                'cached_at': datetime.now().isoformat()
            }

            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cached_data, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def evaluate_reranking(
        self,
        query: str,
        candidates: List[Dict],
        ground_truth_ids: List[str]
    ) -> Dict[str, float]:
        """评估重排序效果

        Args:
            query: 搜索查询
            candidates: 候选结果
            ground_truth_ids: 正确结果的ID列表（按相关性排序）

        Returns:
            评估指标字典（MRR, NDCG@5, NDCG@10, etc.）
        """
        # 执行重排
        reranked = await self.rerank(query, candidates, use_cache=False)

        # 提取重排后的ID列表
        reranked_ids = [r.get('memory_id') for r in reranked]

        # 计算 MRR
        mrr = self._calculate_mrr(reranked_ids, ground_truth_ids)

        # 计算 NDCG
        ndcg_5 = self._calculate_ndcg(reranked_ids, ground_truth_ids, k=5)
        ndcg_10 = self._calculate_ndcg(reranked_ids, ground_truth_ids, k=10)

        return {
            'mrr': mrr,
            'ndcg@5': ndcg_5,
            'ndcg@10': ndcg_10,
            'num_reranked': len(reranked),
            'num_candidates': len(candidates)
        }

    def _calculate_mrr(self, ranked_ids: List[str], ground_truth_ids: List[str]) -> float:
        """计算 MRR (Mean Reciprocal Rank)

        Args:
            ranked_ids: 排序后的ID列表
            ground_truth_ids: 正确结果ID列表

        Returns:
            MRR 分数
        """
        for i, rid in enumerate(ranked_ids):
            if rid in ground_truth_ids:
                return 1.0 / (i + 1)
        return 0.0

    def _calculate_ndcg(self, ranked_ids: List[str], ground_truth_ids: List[str], k: int = 10) -> float:
        """计算 NDCG@K (Normalized Discounted Cumulative Gain)

        Args:
            ranked_ids: 排序后的ID列表
            ground_truth_ids: 正确结果ID列表
            k: Top-K

        Returns:
            NDCG@K 分数
        """
        if not ground_truth_ids:
            return 0.0

        # 计算 DCG
        dcg = 0.0
        for i in range(min(k, len(ranked_ids))):
            if ranked_ids[i] in ground_truth_ids:
                # 假设所有正确结果的增益都是1（二值相关性）
                dcg += 1.0 / math.log2(i + 2)

        # 计算 Ideal DCG (理想情况下，所有正确结果都在最前面)
        idcg = 0.0
        for i in range(min(k, len(ground_truth_ids))):
            idcg += 1.0 / math.log2(i + 2)

        return dcg / idcg if idcg > 0 else 0.0

    async def clear_cache(self, query: Optional[str] = None, memory_ids: Optional[List[str]] = None):
        """清理缓存

        Args:
            query: 搜索查询（如果提供，只清理该查询的缓存）
            memory_ids: 记忆ID列表（如果提供，只清理相关缓存）
        """
        if query and memory_ids:
            cache_key = self._get_cache_key(query, memory_ids)
            await self.redis.delete(cache_key)
        else:
            # 清理所有重排缓存（需要扫描所有键）
            # 注意：这在大规模场景下可能很慢
            import asyncio
            keys = []
            async for key in self.redis.scan_iter(match="rerank:*"):
                keys.append(key)
            if keys:
                await self.redis.delete(*keys)


# 全局单例
_reranking_service: Optional[RerankingService] = None


def get_reranking_service(
    model_name: str = "BAAI/bge-reranker-large",
    top_k: int = 20,
    threshold: float = 0.5
) -> RerankingService:
    """获取重排序服务单例

    Args:
        model_name: 模型名称
        top_k: Top-K 数量
        threshold: 阈值

    Returns:
        RerankingService 实例
    """
    global _reranking_service
    if _reranking_service is None:
        _reranking_service = RerankingService(
            model_name=model_name,
            top_k=top_k,
            threshold=threshold
        )
    return _reranking_service


def reset_reranking_service():
    """重置重排序服务（用于测试）"""
    global _reranking_service
    _reranking_service = None
