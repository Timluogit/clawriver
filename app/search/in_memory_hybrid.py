"""内存混合搜索引擎

纯内存架构的混合搜索：向量 + 关键词 + 重排
三级降级策略：全功能 → 向量搜索 → 关键词搜索
"""
import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.services.memory_index import MemoryIndex, get_memory_index, MemoryEntry
from app.search.in_memory_vector import InMemoryVectorEngine, get_in_memory_vector_engine

logger = logging.getLogger(__name__)


class SearchMode:
    """搜索模式"""
    FULL = "full"           # 向量 + 关键词 + 重排
    VECTOR_ONLY = "vector"  # 仅向量搜索
    KEYWORD_ONLY = "keyword"  # 仅关键词搜索


class InMemoryHybridEngine:
    """内存混合搜索引擎

    三级降级策略：
    1. 全功能模式 (full): 向量 + 关键词 + 重排
    2. 向量模式 (vector): 仅向量搜索（无关键词/无重排）
    3. 关键词模式 (keyword): 仅倒排索引关键词搜索（无需向量）

    所有操作均在内存中完成，无需外部数据库。
    """

    def __init__(
        self,
        index: Optional[MemoryIndex] = None,
        vector_engine: Optional[InMemoryVectorEngine] = None,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        enable_rerank: bool = True,
    ):
        """初始化混合搜索引擎

        Args:
            index: 内存索引实例
            vector_engine: 向量搜索引擎实例
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
            enable_rerank: 是否启用重排
        """
        self.index = index or get_memory_index()
        self.vector_engine = vector_engine or get_in_memory_vector_engine(index=self.index)
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.enable_rerank = enable_rerank

        # 统计
        self.stats = {
            'total_searches': 0,
            'total_search_time': 0.0,
            'avg_search_time': 0.0,
            'mode_counts': {'full': 0, 'vector': 0, 'keyword': 0},
        }

    def search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        top_k: int = 50,
        min_score: float = 0.1,
        search_mode: str = SearchMode.FULL,
        filter_category: Optional[str] = None,
        filter_tag: Optional[str] = None,
        filter_seller: Optional[str] = None,
        filter_expired: bool = True,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """混合搜索

        Args:
            query: 搜索查询文本
            query_vector: 查询向量（可选，用于向量搜索）
            top_k: 从搜索中选取的候选数
            min_score: 最小分数阈值
            search_mode: 搜索模式 (full/vector/keyword)
            filter_category: 分类过滤
            filter_tag: 标签过滤
            filter_seller: 卖家过滤
            filter_expired: 是否过滤过期记忆
            sort_by: 排序方式 (relevance/time/popularity/price)
            page: 页码
            page_size: 每页数量

        Returns:
            {
                'items': [...],
                'total': int,
                'page': int,
                'page_size': int,
                'search_mode': str,
                'search_time': float,
            }
        """
        start_time = time.time()

        if self.index.is_empty():
            return self._empty_result(page, page_size, search_mode, 0)

        # 获取所有条目并过滤
        all_entries = self.index.get_all_entries()
        candidate_ids = set(all_entries.keys())

        # 元数据过滤
        if filter_category:
            cat_ids = self.index.filter_by_category(filter_category)
            candidate_ids &= cat_ids
        if filter_tag:
            tag_ids = self.index.filter_by_tag(filter_tag)
            candidate_ids &= tag_ids
        if filter_seller:
            seller_ids = self.index.filter_by_seller(filter_seller)
            candidate_ids &= seller_ids

        # 过滤过期记忆
        if filter_expired:
            now = time.time()
            expired_ids = set()
            for mid in candidate_ids:
                entry = all_entries.get(mid)
                if entry and entry.expiry_time and entry.expiry_time < now:
                    expired_ids.add(mid)
                if entry and not entry.is_active:
                    expired_ids.add(mid)
            candidate_ids -= expired_ids

        if not candidate_ids:
            return self._empty_result(page, page_size, search_mode, 0)

        # 根据搜索模式执行搜索
        scored_results: Dict[str, float] = {}

        if search_mode == SearchMode.KEYWORD_ONLY:
            # 纯关键词搜索
            keyword_results = self.index.keyword_search(query, top_k=top_k)
            scored_results = {
                mid: score for mid, score in keyword_results
                if mid in candidate_ids
            }
            self.stats['mode_counts']['keyword'] += 1

        elif search_mode == SearchMode.VECTOR_ONLY and query_vector is not None:
            # 纯向量搜索
            vector_results = self.vector_engine.search(
                query_vector, top_k=top_k, min_score=min_score,
                filter_ids=candidate_ids
            )
            scored_results = {mid: score for mid, score in vector_results}
            self.stats['mode_counts']['vector'] += 1

        else:
            # 全功能模式 (默认)
            scored_results = self._full_search(
                query, query_vector, candidate_ids, all_entries,
                top_k, min_score
            )
            self.stats['mode_counts']['full'] += 1

        # 重排
        if self.enable_rerank and search_mode != SearchMode.KEYWORD_ONLY:
            scored_results = self._rerank(query, scored_results, all_entries)

        # 排序
        if sort_by == "time":
            sorted_ids = sorted(
                scored_results.keys(),
                key=lambda mid: all_entries[mid].updated_at if mid in all_entries else 0,
                reverse=True
            )
        elif sort_by == "popularity":
            sorted_ids = sorted(
                scored_results.keys(),
                key=lambda mid: all_entries[mid].purchase_count if mid in all_entries else 0,
                reverse=True
            )
        elif sort_by == "price":
            sorted_ids = sorted(
                scored_results.keys(),
                key=lambda mid: all_entries[mid].price if mid in all_entries else 0
            )
        else:
            # relevance (默认)
            sorted_ids = sorted(
                scored_results.keys(),
                key=lambda mid: scored_results[mid],
                reverse=True
            )

        # 分页
        total = len(sorted_ids)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_ids = sorted_ids[start_idx:end_idx]

        # 构建结果
        items = []
        for mid in page_ids:
            entry = all_entries.get(mid)
            if entry:
                items.append({
                    'memory_id': entry.memory_id,
                    'title': entry.title,
                    'summary': entry.summary,
                    'category': entry.category,
                    'tags': entry.tags,
                    'price': entry.price,
                    'purchase_count': entry.purchase_count,
                    'avg_score': entry.avg_score,
                    'verification_score': entry.verification_score,
                    'created_at': entry.created_at,
                    'updated_at': entry.updated_at,
                    'seller_name': entry.seller_name,
                    'seller_reputation': entry.seller_reputation,
                    'relevance_score': scored_results.get(mid, 0),
                })

        elapsed = time.time() - start_time
        self.stats['total_searches'] += 1
        self.stats['total_search_time'] += elapsed
        self.stats['avg_search_time'] = self.stats['total_search_time'] / self.stats['total_searches']

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'search_mode': search_mode,
            'search_time': round(elapsed, 4),
        }

    def _full_search(
        self,
        query: str,
        query_vector: Optional[List[float]],
        candidate_ids: Set[str],
        all_entries: Dict[str, MemoryEntry],
        top_k: int,
        min_score: float
    ) -> Dict[str, float]:
        """全功能搜索：向量 + 关键词融合

        Args:
            query: 查询文本
            query_vector: 查询向量
            candidate_ids: 候选记忆ID集合
            all_entries: 所有条目
            top_k: 返回数量
            min_score: 最小分数

        Returns:
            {memory_id: score}
        """
        hybrid_scores: Dict[str, float] = {}

        # 1. 向量搜索
        if query_vector is not None:
            vector_results = self.vector_engine.search(
                query_vector, top_k=top_k * 2, min_score=min_score,
                filter_ids=candidate_ids
            )
            if vector_results:
                max_v_score = max(score for _, score in vector_results)
                if max_v_score > 0:
                    for mid, score in vector_results:
                        hybrid_scores[mid] = (score / max_v_score) * self.semantic_weight

        # 2. 关键词搜索
        keyword_results = self.index.keyword_search(query, top_k=top_k * 2)
        for mid, score in keyword_results:
            if mid not in candidate_ids:
                continue
            if mid in hybrid_scores:
                hybrid_scores[mid] += score * self.keyword_weight
            else:
                hybrid_scores[mid] = score * self.keyword_weight * 0.5

        # 过滤低分
        hybrid_scores = {k: v for k, v in hybrid_scores.items() if v >= min_score}

        return hybrid_scores

    def _rerank(
        self,
        query: str,
        scores: Dict[str, float],
        all_entries: Dict[str, MemoryEntry]
    ) -> Dict[str, float]:
        """规则重排

        综合考虑：
        - 文本精确匹配（标题/摘要）
        - 信号质量（评分、购买数、验证分）
        - 时效性
        - 价格合理性
        """
        reranked: Dict[str, float] = {}
        query_lower = query.lower()

        for mid, base_score in scores.items():
            entry = all_entries.get(mid)
            if not entry:
                continue

            # 文本精确匹配
            text_sim = 0.0
            title_lower = entry.title.lower()
            summary_lower = entry.summary.lower()

            if query_lower in title_lower:
                text_sim += 0.3
            if query_lower in summary_lower:
                text_sim += 0.2

            # 信号质量
            signal_score = 0.0
            if entry.avg_score:
                signal_score += (entry.avg_score / 5.0) * 0.2
            if entry.purchase_count:
                signal_score += min(math.log10(entry.purchase_count + 1) / math.log10(100), 0.3)
            if entry.verification_score:
                signal_score += entry.verification_score * 0.2

            # 时效性
            time_score = 0.0
            if entry.created_at:
                days_old = (time.time() - entry.created_at) / 86400
                if days_old <= 7:
                    time_score = 0.1
                elif days_old <= 30:
                    time_score = 0.05

            # 价格合理性
            price_score = 0.0
            if 0 < entry.price <= 100:
                price_score = 0.1
            elif 0 < entry.price <= 300:
                price_score = 0.05

            reranked[mid] = (
                base_score * 0.5 +
                text_sim +
                signal_score +
                time_score +
                price_score
            )

        return reranked

    def _empty_result(self, page: int, page_size: int, mode: str, elapsed: float) -> Dict:
        """空结果"""
        return {
            'items': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'search_mode': mode,
            'search_time': round(elapsed, 4),
        }

    def get_stats(self) -> Dict:
        """获取搜索统计"""
        return {
            **self.stats,
            'vector_stats': self.vector_engine.get_stats() if self.vector_engine else {},
            'index_stats': self.index.stats,
        }

    def clear_stats(self):
        """清除统计"""
        self.stats = {
            'total_searches': 0,
            'total_search_time': 0.0,
            'avg_search_time': 0.0,
            'mode_counts': {'full': 0, 'vector': 0, 'keyword': 0},
        }


# 全局单例
_hybrid_engine: Optional[InMemoryHybridEngine] = None


def get_in_memory_hybrid_engine(
    index: Optional[MemoryIndex] = None,
    vector_engine: Optional[InMemoryVectorEngine] = None,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
    enable_rerank: bool = True,
) -> InMemoryHybridEngine:
    """获取内存混合搜索引擎单例"""
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = InMemoryHybridEngine(
            index=index,
            vector_engine=vector_engine,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            enable_rerank=enable_rerank,
        )
    return _hybrid_engine
