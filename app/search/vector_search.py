"""向量语义搜索引擎

使用纯 Python TF-IDF + 余弦相似度实现轻量级语义搜索
无需 scikit-learn，节省约 200MB 内存
"""
import math
import pickle
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set


# ---------------------------------------------------------------------------
# 纯 Python TF-IDF 实现
# ---------------------------------------------------------------------------

class _TfidfVectorizer:
    """轻量级 TF-IDF 向量化器（替代 sklearn.feature_extraction.text.TfidfVectorizer）

    特性：
    - 字符级 ngram（支持中文）
    - sublinear TF（log(1+tf)）
    - IDF 平滑（log((N+1)/(df+1))+1）
    - 最大特征数限制
    """

    def __init__(
        self,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 3),
        sublinear_tf: bool = True,
        analyzer: str = "char_wb",
    ):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.sublinear_tf = sublinear_tf
        self.analyzer = analyzer

        self.vocabulary_: Dict[str, int] = {}
        self.idf_: List[float] = []
        self._is_fitted = False

    # ------------------------------------------------------------------
    # 分词 / ngram
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> List[str]:
        """提取字符级 ngram"""
        text = text.lower().strip()
        min_n, max_n = self.ngram_range
        tokens: List[str] = []
        if self.analyzer == "char_wb":
            # 在词边界处用空格填充（char_wb 风格）
            for word in re.split(r"\s+", text):
                word = " " + word + " "
                for n in range(min_n, max_n + 1):
                    for i in range(len(word) - n + 1):
                        tokens.append(word[i: i + n])
        else:
            for n in range(min_n, max_n + 1):
                for i in range(len(text) - n + 1):
                    tokens.append(text[i: i + n])
        return tokens

    # ------------------------------------------------------------------
    # fit / transform
    # ------------------------------------------------------------------

    def fit_transform(self, texts: List[str]) -> List[Dict[int, float]]:
        """拟合并转换文本列表，返回稀疏向量列表（Dict[feature_index, tfidf_value]）"""
        # 1. 统计 df
        df: Counter = Counter()
        tokenized: List[List[str]] = []
        for text in texts:
            tokens = self._tokenize(text)
            tokenized.append(tokens)
            df.update(set(tokens))

        N = len(texts)

        # 2. 选取最高频 ngram 作为词表
        top_ngrams = [tok for tok, _ in df.most_common(self.max_features)]
        self.vocabulary_ = {tok: idx for idx, tok in enumerate(top_ngrams)}
        vocab_size = len(self.vocabulary_)

        # 3. 计算 IDF（平滑）
        self.idf_ = [0.0] * vocab_size
        for tok, idx in self.vocabulary_.items():
            df_val = df[tok]
            self.idf_[idx] = math.log((N + 1) / (df_val + 1)) + 1.0

        self._is_fitted = True

        # 4. 计算 TF-IDF 向量
        return [self._transform_one(tokens) for tokens in tokenized]

    def transform(self, texts: List[str]) -> List[Dict[int, float]]:
        """仅转换（词表已固定）"""
        if not self._is_fitted:
            raise RuntimeError("Vectorizer not fitted yet")
        return [self._transform_one(self._tokenize(t)) for t in texts]

    def _transform_one(self, tokens: List[str]) -> Dict[int, float]:
        """计算单个文档的 TF-IDF 稀疏向量"""
        tf_counter: Counter = Counter(tokens)
        vec: Dict[int, float] = {}
        norm_sq = 0.0

        for tok, raw_tf in tf_counter.items():
            idx = self.vocabulary_.get(tok)
            if idx is None:
                continue
            tf = (1.0 + math.log(raw_tf)) if self.sublinear_tf else float(raw_tf)
            val = tf * self.idf_[idx]
            vec[idx] = val
            norm_sq += val * val

        # L2 归一化
        if norm_sq > 0:
            norm = math.sqrt(norm_sq)
            vec = {k: v / norm for k, v in vec.items()}

        return vec


def _cosine_similarity_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    """两个已 L2 归一化的稀疏向量点积 = 余弦相似度"""
    dot = 0.0
    # 遍历较短的向量
    if len(a) > len(b):
        a, b = b, a
    for idx, val in a.items():
        if idx in b:
            dot += val * b[idx]
    return dot


# ---------------------------------------------------------------------------
# 搜索引擎
# ---------------------------------------------------------------------------

class VectorSearchEngine:
    """向量搜索引擎

    使用纯 Python TF-IDF + 余弦相似度进行语义搜索，
    无需 scikit-learn / numpy 等重量级依赖。
    """

    def __init__(self, cache_dir: str = "/tmp/clawriver_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.vectorizer = _TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            sublinear_tf=True,
            analyzer="char_wb",
        )

        # 稀疏向量列表（每个元素是 Dict[feature_index, tfidf_value]）
        self._memory_vectors: List[Dict[int, float]] = []
        self._memory_ids: List[str] = []
        self._is_fitted = False

    # ------------------------------------------------------------------
    # 缓存
    # ------------------------------------------------------------------

    def _get_cache_path(self) -> Path:
        return self.cache_dir / "tfidf_cache.pkl"

    def _compute_hash(self, memories: List[Dict]) -> str:
        content = sorted(f"{m['id']}:{m['title']}:{m['summary']}" for m in memories)
        return hashlib.md5("|".join(content).encode()).hexdigest()

    def _save_cache(self) -> None:
        if not self._memory_vectors:
            return
        cache_data = {
            "vectorizer": self.vectorizer,
            "memory_vectors": self._memory_vectors,
            "memory_ids": self._memory_ids,
            "is_fitted": self._is_fitted,
        }
        with open(self._get_cache_path(), "wb") as f:
            pickle.dump(cache_data, f)

    def _load_cache(self, current_hash: str) -> bool:
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False
        try:
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)
            if current_hash and cache_data.get("hash") != current_hash:
                return False
            self.vectorizer = cache_data["vectorizer"]
            self._memory_vectors = cache_data["memory_vectors"]
            self._memory_ids = cache_data["memory_ids"]
            self._is_fitted = cache_data["is_fitted"]
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 索引
    # ------------------------------------------------------------------

    def index_memories(self, memories: List[Dict]) -> None:
        if not memories:
            return
        texts = []
        self._memory_ids = []
        for m in memories:
            texts.append(f"{m.get('title', '')} {m.get('summary', '')}")
            self._memory_ids.append(m["id"])

        self._memory_vectors = self.vectorizer.fit_transform(texts)
        self._is_fitted = True
        self._save_cache()

    def batch_index_with_cache(
        self, memories: List[Dict], force_rebuild: bool = False
    ) -> None:
        if not memories:
            return
        current_hash = self._compute_hash(memories)
        if not force_rebuild and self._load_cache(current_hash):
            return
        self.index_memories(memories)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 50,
        min_similarity: float = 0.1,
    ) -> List[Tuple[str, float]]:
        if not self._is_fitted or not self._memory_vectors:
            return []

        query_vec = self.vectorizer.transform([query])[0]
        if not query_vec:
            return []

        scored: List[Tuple[str, float]] = []
        for mid, mem_vec in zip(self._memory_ids, self._memory_vectors):
            score = _cosine_similarity_sparse(query_vec, mem_vec)
            if score >= min_similarity:
                scored.append((mid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_with_keywords(
        self,
        query: str,
        keyword_ids: set,
        top_k: int = 50,
        min_similarity: float = 0.1,
        semantic_weight: float = 0.5,
    ) -> List[Tuple[str, float]]:
        semantic_results = self.search(query, top_k=top_k * 2, min_similarity=min_similarity)

        if semantic_results:
            max_score = max(s for _, s in semantic_results)
            if max_score > 0:
                semantic_results = [(mid, s / max_score) for mid, s in semantic_results]

        hybrid_scores: Dict[str, float] = {}
        for memory_id, score in semantic_results:
            hybrid_scores[memory_id] = score * semantic_weight

        for memory_id in keyword_ids:
            if memory_id in hybrid_scores:
                hybrid_scores[memory_id] += (1 - semantic_weight)
            else:
                hybrid_scores[memory_id] = (1 - semantic_weight) * 0.5

        sorted_results = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def get_memory_count(self) -> int:
        return len(self._memory_ids)

    def clear_cache(self) -> None:
        cache_path = self._get_cache_path()
        if cache_path.exists():
            cache_path.unlink()
        self._memory_vectors = []
        self._memory_ids = []
        self._is_fitted = False


# 全局单例
_engine: Optional[VectorSearchEngine] = None


def get_search_engine() -> VectorSearchEngine:
    global _engine
    if _engine is None:
        _engine = VectorSearchEngine()
    return _engine
