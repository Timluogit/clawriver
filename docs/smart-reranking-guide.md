# 智能重排指南 (Smart Reranking Guide)

> ClawRiver P4.4 - 对标 Supermemory 99% 准确率

## 概述

智能重排系统通过多维度加权融合，对搜索结果进行精细排序，显著提升检索准确率。

### 核心特性

| 特性 | 说明 |
|------|------|
| 多维度评分 | 语义、关键词、时效性、用户偏好、记忆质量 5 大维度 15 个特征 |
| 加权融合 | 可配置权重的加权融合算法 |
| 动态权重 | 基于查询类型和用户画像自动调整权重 |
| Cross-Encoder | 集成 BAAI/bge-reranker-large 进行深度语义理解 |
| 策略预设 | 6 种预设策略，覆盖主流场景 |
| A/B 测试 | 内置对比测试框架 |
| 缓存优化 | 结果缓存 + 特征缓存 |

### 与旧版对比

| 维度 | 旧版 (P4.3) | 新版 (P4.4) |
|------|------------|------------|
| 特征数 | 4 | 15 |
| 评分维度 | 2 (语义+规则) | 5 (语义/关键词/时效/偏好/质量) |
| 权重调整 | 固定 | 动态自适应 |
| 用户画像 | 后处理 | 特征级别融合 |
| 评估指标 | MRR | MRR/NDCG/MAP/Precision/Recall |
| A/B 测试 | 无 | 内置支持 |

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                  SmartRerankingService            │
│                                                   │
│  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ CrossEncoder  │  │   FeatureExtractor        │ │
│  │ 语义评分       │  │ 15维特征提取              │ │
│  └──────┬───────┘  └──────────┬────────────────┘ │
│         │                     │                   │
│         ▼                     ▼                   │
│  ┌──────────────────────────────────────────┐    │
│  │         Dynamic Weight Adjustment        │    │
│  │         动态权重调整引擎                   │    │
│  └──────────────────┬───────────────────────┘    │
│                     │                             │
│                     ▼                             │
│  ┌──────────────────────────────────────────┐    │
│  │         Weighted Fusion Score            │    │
│  │         加权融合 → final_score            │    │
│  └──────────────────┬───────────────────────┘    │
│                     │                             │
│                     ▼                             │
│  ┌──────────────────────────────────────────┐    │
│  │    Sort → Threshold → Top-K → Output     │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │    RerankingEvaluator (MRR/NDCG/MAP)     │    │
│  │    ABTester (策略对比)                    │    │
│  │    EvalHistory (评估历史)                 │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 特征体系

### 1. 语义特征 (Semantic)

| 特征 | 说明 | 范围 |
|------|------|------|
| `semantic_score` | Cross-Encoder 语义匹配分数 | 0-1 |
| `embedding_similarity` | 向量余弦相似度 | 0-1 |

### 2. 关键词特征 (Keyword)

| 特征 | 说明 | 范围 |
|------|------|------|
| `keyword_exact_match` | 查询词在内容中的覆盖率 | 0-1 |
| `keyword_bm25_score` | BM25 风格得分 | 0-1 |
| `keyword_title_match` | 标题是否包含关键词 | 0/1 |
| `keyword_tag_match` | 标签匹配度 | 0-1 |

### 3. 时效性特征 (Recency)

| 特征 | 说明 | 范围 |
|------|------|------|
| `recency_score` | 指数衰减（半衰期30天） | 0-1 |
| `freshness_score` | 7天内=1.0，线性衰减 | 0.1-1.0 |

### 4. 用户偏好特征 (Personalization)

| 特征 | 说明 | 范围 |
|------|------|------|
| `user_interest_match` | 兴趣/研究领域匹配 | 0-1 |
| `user_history_match` | 历史偏好匹配 | 0-1 |
| `user_category_affinity` | 分类亲和度 | 0-1 |

### 5. 记忆质量特征 (Quality)

| 特征 | 说明 | 范围 |
|------|------|------|
| `quality_signal` | 综合信号质量 | 0-1 |
| `purchase_popularity` | 购买热度（log平滑） | 0-1 |
| `rating_score` | 评分归一化 | 0-1 |
| `verification_strength` | 验证强度 | 0-1 |

---

## 预设策略

| 策略 | 适用场景 | 语义权重 | 关键词权重 | 时效权重 | 质量权重 | 偏好权重 |
|------|---------|---------|-----------|---------|---------|---------|
| `balanced` | 通用场景 | 40% | 23% | 10% | 15% | 12% |
| `semantic_heavy` | 复杂语义查询 | 60% | 15% | 8% | 5% | 12% |
| `keyword_heavy` | 精确匹配场景 | 20% | 53% | 8% | 10% | 9% |
| `freshness_first` | 新闻/动态 | 28% | 20% | 27% | 13% | 12% |
| `quality_first` | 高可信度需求 | 30% | 18% | 8% | 35% | 9% |
| `personalized` | 有用户画像 | 28% | 16% | 8% | 18% | 30% |

---

## API 端点

### POST `/api/reranking/rank`
手动重排候选列表。

```json
{
  "query": "Python FastAPI 教程",
  "candidates": [
    {
      "memory_id": "mem_001",
      "title": "FastAPI 入门指南",
      "summary": "...",
      "content_text": "...",
      "tags": ["python", "fastapi"],
      "category": "编程",
      "created_at": "2025-06-10T10:00:00",
      "avg_score": 4.5,
      "purchase_count": 50
    }
  ],
  "user_profile": {          // 可选
    "interests": ["Python"],
    "preferred_categories": ["编程"]
  },
  "top_k": 10,               // 可选
  "strategy": "balanced"     // 可选
}
```

### GET `/api/reranking/config`
获取当前配置和可用策略。

### PUT `/api/reranking/config`
动态更新配置。

```json
{
  "strategy": "semantic_heavy",
  "top_k": 15,
  "enable_dynamic_weights": true
}
```

### POST `/api/reranking/evaluate`
运行评估。

```json
{
  "test_cases": [
    {
      "query": "Python 教程",
      "candidates": [...],
      "expected_ids": ["mem_001", "mem_003"]
    }
  ],
  "strategy": "balanced"
}
```

### POST `/api/reranking/ab-test`
A/B 测试。

```json
{
  "test_cases": [...],
  "strategy_a": "balanced",
  "strategy_b": "semantic_heavy"
}
```

### GET `/api/reranking/stats`
获取运行统计（调用次数、缓存命中率、平均延迟等）。

### GET `/api/reranking/strategies`
列出所有预设策略及权重。

### GET `/api/reranking/eval/history`
评估历史。

### GET `/api/reranking/eval/compare?ids=r1,r2`
对比评估结果。

---

## 配置项 (环境变量)

```bash
# 基础配置
SMART_RERANK_ENABLED=true
SMART_RERANK_STRATEGY=balanced        # 预设策略名称
SMART_RERANK_USE_CROSS_ENCODER=true
SMART_RERANK_CE_WEIGHT=0.70           # Cross-Encoder 在融合中的权重
SMART_RERANK_DYNAMIC_WEIGHTS=true
SMART_RERANK_TOP_K=20
SMART_RERANK_THRESHOLD=0.0
SMART_RERANK_MIN_CANDIDATES=5
SMART_RERANK_CACHE_ENABLED=true
SMART_RERANK_CACHE_TTL=3600

# 自定义权重（覆盖策略预设）
SMART_RERANK_W_SEMANTIC=0.30
SMART_RERANK_W_EMBEDDING=0.10
SMART_RERANK_W_KW_EXACT=0.08
SMART_RERANK_W_KW_BM25=0.07
SMART_RERANK_W_KW_TITLE=0.05
SMART_RERANK_W_KW_TAG=0.03
SMART_RERANK_W_RECENCY=0.06
SMART_RERANK_W_FRESHNESS=0.04
SMART_RERANK_W_INTEREST=0.05
SMART_RERANK_W_HISTORY=0.04
SMART_RERANK_W_CATEGORY=0.03
SMART_RERANK_W_QUALITY=0.05
SMART_RERANK_W_POPULARITY=0.04
SMART_RERANK_W_RATING=0.03
SMART_RERANK_W_VERIFICATION=0.03
```

---

## 动态权重调整规则

| 条件 | 调整 |
|------|------|
| 短查询（≤3词） | 提升关键词权重 +5% |
| 长查询（>10词） | 提升语义权重 +8% |
| 有用户画像 | 提升个性化权重 +4% |
| 候选分数集中（std<0.1） | 提升质量权重 +3% |

调整后自动归一化到 1.0。

---

## 评估指标

| 指标 | 说明 |
|------|------|
| MRR | Mean Reciprocal Rank，首个正确结果的倒数排名 |
| NDCG@5/10/20 | 归一化折损累积增益 |
| Precision@5/10 | Top-K 中正确结果的比例 |
| MAP | Mean Average Precision |
| Recall@10 | Top-K 中正确结果的召回率 |
| Hit Rate | Top-10 中至少命中一个正确结果的概率 |
| Composite Score | 综合加权得分（MRR×0.25 + NDCG@10×0.30 + Precision@10×0.20 + MAP×0.15 + Hit Rate×0.10） |

---

## 与现有系统集成

智能重排已集成到 `HybridSearchEngine._rerank()` 方法中。当 `SMART_RERANK_ENABLED=true` 时，搜索会自动使用智能重排替代旧版规则重排。

旧版 `RerankingService`（纯 Cross-Encoder）保留作为兼容层，可独立使用。

---

## 文件结构

```
app/
  services/
    smart_reranking.py      # 智能重排核心服务
    reranking_features.py   # 特征工程
    reranking_eval.py       # 评估集成
    reranking_service.py    # 旧版 Cross-Encoder（保留兼容）
  api/
    reranking.py            # API 端点
  core/
    config.py               # 新增 SMART_RERANK_* 配置
tests/
  test_smart_reranking.py   # 测试套件
docs/
  smart-reranking-guide.md  # 本文档
```
