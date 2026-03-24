"""向量语义搜索引擎

使用 TF-IDF + 余弦相似度实现轻量级语义搜索
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import hashlib
from pathlib import Path


class VectorSearchEngine:
    """向量搜索引擎

    使用 TF-IDF 向量化 + 余弦相似度进行语义搜索
    """

    def __init__(self, cache_dir: str = "/tmp/clawriver_cache"):
        """初始化搜索引擎

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # TF-IDF 向量化器
        # 针对中文优化：使用字符级 ngram，不使用停用词
        # min_df=1, max_df=1.0 保证在任何文档数量下都能工作
        self.vectorizer = TfidfVectorizer(
            max_features=5000,  # 最大特征数
            ngram_range=(1, 3),  # 1-3 gram，对中文更友好
            min_df=1,  # 最小文档频率
            max_df=1.0,  # 最大文档频率（不过滤，避免小数据集冲突）
            sublinear_tf=True,  # 使用对数 TF 缩放
            analyzer='char_wb',  # 字符级分析，支持中文
            stop_words=None  # 不使用停用词（支持多语言）
        )

        # 内存缓存
        self._memory_vectors: Optional[np.ndarray] = None
        self._memory_ids: List[str] = []
        self._is_fitted = False

    def _get_cache_path(self) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / "tfidf_cache.pkl"

    def _compute_hash(self, memories: List[Dict]) -> str:
        """计算记忆列表的哈希值，用于检测变化"""
        content = sorted(f"{m['id']}:{m['title']}:{m['summary']}" for m in memories)
        return hashlib.md5("|".join(content).encode()).hexdigest()

    def index_memories(self, memories: List[Dict]) -> None:
        """索引记忆

        Args:
            memories: 记忆列表，每个记忆包含 id, title, summary
        """
        if not memories:
            return

        # 准备文本：标题 + 摘要
        texts = []
        self._memory_ids = []
        for m in memories:
            text = f"{m.get('title', '')} {m.get('summary', '')}"
            texts.append(text)
            self._memory_ids.append(m['id'])

        # 训练或更新 TF-IDF 模型
        if not self._is_fitted:
            # 首次训练
            self._memory_vectors = self.vectorizer.fit_transform(texts)
            self._is_fitted = True
        else:
            # 增量更新：重新训练（简化方案）
            # 对于生产环境，可以考虑使用在线学习算法
            self._memory_vectors = self.vectorizer.fit_transform(texts)

        # 保存到缓存
        self._save_cache()

    def _save_cache(self) -> None:
        """保存索引到缓存"""
        if self._memory_vectors is None:
            return

        cache_data = {
            'vectorizer': self.vectorizer,
            'memory_vectors': self._memory_vectors,
            'memory_ids': self._memory_ids,
            'is_fitted': self._is_fitted
        }

        with open(self._get_cache_path(), 'wb') as f:
            pickle.dump(cache_data, f)

    def _load_cache(self, current_hash: str) -> bool:
        """从缓存加载索引

        Args:
            current_hash: 当前数据的哈希值

        Returns:
            是否成功加载
        """
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)

            # 检查哈希是否匹配（如果有提供）
            if current_hash and cache_data.get('hash') != current_hash:
                return False

            self.vectorizer = cache_data['vectorizer']
            self._memory_vectors = cache_data['memory_vectors']
            self._memory_ids = cache_data['memory_ids']
            self._is_fitted = cache_data['is_fitted']

            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        top_k: int = 50,
        min_similarity: float = 0.1
    ) -> List[Tuple[str, float]]:
        """语义搜索

        Args:
            query: 搜索查询
            top_k: 返回前 k 个结果
            min_similarity: 最小相似度阈值

        Returns:
            [(memory_id, similarity_score), ...] 按相似度降序排序
        """
        if not self._is_fitted or self._memory_vectors is None:
            return []

        # 查询向量化
        query_vector = self.vectorizer.transform([query])

        # 计算余弦相似度
        similarities = cosine_similarity(query_vector, self._memory_vectors)[0]

        # 排序并过滤
        indices = np.argsort(similarities)[::-1]  # 降序

        results = []
        for idx in indices:
            score = float(similarities[idx])
            if score >= min_similarity and len(results) < top_k:
                results.append((self._memory_ids[idx], score))

        return results

    def search_with_keywords(
        self,
        query: str,
        keyword_ids: set,
        top_k: int = 50,
        min_similarity: float = 0.1,
        semantic_weight: float = 0.5
    ) -> List[Tuple[str, float]]:
        """混合搜索：语义 + 关键词

        Args:
            query: 搜索查询
            keyword_ids: 关键词匹配的记忆 ID 集合
            top_k: 返回前 k 个结果
            min_similarity: 最小相似度阈值
            semantic_weight: 语义搜索权重 (0-1)，关键词权重为 1-semantic_weight

        Returns:
            [(memory_id, hybrid_score), ...] 按混合分数降序排序
        """
        # 语义搜索结果
        semantic_results = self.search(query, top_k=top_k * 2, min_similarity=min_similarity)

        # 归一化语义分数
        if semantic_results:
            max_semantic_score = max(score for _, score in semantic_results)
            if max_semantic_score > 0:
                semantic_results = [(mid, score / max_semantic_score) for mid, score in semantic_results]

        # 混合评分
        hybrid_scores: Dict[str, float] = {}

        # 语义搜索得分
        for memory_id, score in semantic_results:
            hybrid_scores[memory_id] = score * semantic_weight

        # 关键词匹配加分
        for memory_id in keyword_ids:
            if memory_id in hybrid_scores:
                hybrid_scores[memory_id] += (1 - semantic_weight)
            else:
                hybrid_scores[memory_id] = (1 - semantic_weight) * 0.5

        # 排序
        sorted_results = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_results[:top_k]

    def batch_index_with_cache(
        self,
        memories: List[Dict],
        force_rebuild: bool = False
    ) -> None:
        """批量索引记忆（带缓存）

        Args:
            memories: 记忆列表
            force_rebuild: 是否强制重建索引
        """
        if not memories:
            return

        # 计算哈希
        current_hash = self._compute_hash(memories)

        # 尝试加载缓存
        if not force_rebuild and self._load_cache(current_hash):
            return

        # 重建索引
        self.index_memories(memories)

    def get_memory_count(self) -> int:
        """获取已索引的记忆数量"""
        return len(self._memory_ids)

    def clear_cache(self) -> None:
        """清除缓存"""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            cache_path.unlink()

        self._memory_vectors = None
        self._memory_ids = []
        self._is_fitted = False


# 全局单例
_engine: Optional[VectorSearchEngine] = None


def get_search_engine() -> VectorSearchEngine:
    """获取搜索引擎单例"""
    global _engine
    if _engine is None:
        _engine = VectorSearchEngine()
    return _engine
