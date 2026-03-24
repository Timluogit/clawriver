# 内存运行架构指南

## 概述

ClawRiver 现已支持 **纯内存运行架构**，灵感来自 Supermemory 的设计理念：完全在内存中运行，无需外部向量数据库。

## 架构说明

### 核心组件

```
┌─────────────────────────────────────────────┐
│              InMemoryHybridEngine            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ 向量搜索  │  │ 关键词搜索│  │   重排    │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │              │              │        │
│  ┌────┴──────────────┴──────────────┴────┐   │
│  │          InMemoryVectorEngine          │   │
│  │    (numpy矩阵运算, 余弦/欧氏相似度)     │   │
│  └────────────────┬──────────────────────┘   │
│                   │                          │
│  ┌────────────────┴──────────────────────┐   │
│  │           MemoryIndex                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌─────┐  │   │
│  │  │ 倒排索引  │  │ 向量矩阵 │  │条目 │  │   │
│  │  │(keyword→ │  │ (numpy)  │  │存储 │  │   │
│  │  │  ids)    │  │          │  │     │  │   │
│  │  └──────────┘  └──────────┘  └─────┘  │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 三级降级策略

| 级别 | 模式 | 描述 | 依赖 |
|------|------|------|------|
| 1 | `full` | 向量 + 关键词 + 重排 | 向量数据 + 倒排索引 |
| 2 | `vector` | 仅向量搜索 | 向量数据 |
| 3 | `keyword` | 仅倒排索引关键词搜索 | 倒排索引（无需向量） |

当向量数据不可用时，系统自动降级到关键词搜索模式，保证搜索始终可用。

### 数据结构

#### MemoryIndex（内存索引）
- **倒排索引**: `Dict[str, Set[str]]` — token → memory_ids
- **前缀索引**: `Dict[str, Set[str]]` — prefix → tokens（支持前缀搜索）
- **向量矩阵**: `np.ndarray` — (N, dim) 浮点矩阵
- **元数据索引**: 分类/标签/卖家 → memory_ids

#### 分词策略
- 中文：字符级 unigram + bigram
- 英文：空格分词 + lowercasing
- 数字：保留

## 性能对比

### 基准测试结果（1000条记忆）

| 操作 | 内存模式 | Qdrant模式 | 提升 |
|------|---------|-----------|------|
| 向量搜索 | ~2ms | ~15ms | **7.5x** |
| 关键词搜索 | ~0.5ms | ~50ms (SQL) | **100x** |
| 混合搜索 | ~5ms | ~80ms | **16x** |
| 索引构建 | ~3s | ~10s | **3.3x** |

> 实际性能取决于硬件配置和数据规模。内存模式在小到中规模数据集（<100K条）上优势显著。

### 内存占用估算

| 记忆数量 | 向量维度 | 预估内存 |
|---------|---------|---------|
| 1,000 | 512 | ~15 MB |
| 10,000 | 512 | ~150 MB |
| 50,000 | 512 | ~750 MB |
| 100,000 | 512 | ~1.5 GB |

## 配置

在环境变量或 `app/core/config.py` 中配置：

```bash
# 搜索引擎模式: "in-memory" | "qdrant" | "auto"
SEARCH_ENGINE_MODE=in-memory

# 内存索引
MEMORY_INDEX_DIR=./data/memory_index
MEMORY_INDEX_MAX_VECTORS=100000
MEMORY_INDEX_AUTO_PERSIST=true
MEMORY_INDEX_PERSIST_INTERVAL=300  # 5分钟自动持久化

# 向量搜索
IN_MEMORY_SIMILARITY_METRIC=cosine  # cosine | euclidean
IN_MEMORY_BATCH_SIZE=1000

# 混合搜索
IN_MEMORY_SEMANTIC_WEIGHT=0.6
IN_MEMORY_KEYWORD_WEIGHT=0.4
IN_MEMORY_RERANK_ENABLED=true
```

## 使用指南

### 1. 构建索引

```python
from app.services.memory_index import get_memory_index

index = get_memory_index(persist_dir="./data/memory_index")

# 从数据库加载记忆并构建索引
memories = [...]  # 从数据库获取
vectors = [...]   # 对应的嵌入向量（可选）
index.build_index(memories, vectors=vectors)
```

### 2. 向量搜索

```python
from app.search.in_memory_vector import get_in_memory_vector_engine

engine = get_in_memory_vector_engine()
results = engine.search(
    query_vector=query_embedding,
    top_k=10,
    min_score=0.3
)
# results: [(memory_id, score), ...]
```

### 3. 混合搜索

```python
from app.search.in_memory_hybrid import get_in_memory_hybrid_engine

engine = get_in_memory_hybrid_engine()
result = engine.search(
    query="Python异步编程",
    query_vector=query_embedding,  # 可选
    top_k=50,
    filter_category="编程/python",
    filter_tag="python",
    sort_by="relevance",
    page=1,
    page_size=10,
)
# result: {'items': [...], 'total': N, 'search_time': 0.005}
```

### 4. 持久化

```python
# 手动持久化
index.persist()

# 从磁盘加载
index.load()

# 停止服务时自动持久化
index.stop()
```

### 5. 增量更新

```python
# 添加单条记忆
index.add_memory(new_memory, vector=new_vector)

# 更新已有记忆
index.update_memory(updated_memory, vector=updated_vector)

# 删除记忆
index.remove_memory(memory_id)
```

## 与 Qdrant 模式对比

| 特性 | 内存模式 | Qdrant 模式 |
|------|---------|------------|
| 部署复杂度 | 零依赖 | 需要 Qdrant 服务 |
| 搜索延迟 | ~2ms | ~15ms |
| 可扩展性 | 单机（<100K条） | 分布式（百万级） |
| 持久化 | 文件系统 | 内置持久化 |
| 向量索引 | 暴力搜索 | HNSW 索引 |
| 适用场景 | 个人使用、中小规模 | 生产环境、大规模 |

## 何时选择哪种模式

**选择内存模式：**
- 记忆数量 < 100K
- 追求最低搜索延迟
- 不想部署外部数据库
- 个人或小团队使用

**选择 Qdrant 模式：**
- 记忆数量 > 100K
- 需要分布式部署
- 需要高级过滤和聚合
- 生产环境高可用需求

**选择 auto 模式：**
- 希望灵活切换
- Qdrant 可能临时不可用时自动降级

## 持久化策略

内存索引支持自动和手动持久化：

- **自动持久化**: 每隔 `MEMORY_INDEX_PERSIST_INTERVAL` 秒自动保存到磁盘
- **手动持久化**: 调用 `index.persist()`
- **增量持久化**: 仅在数据变化时（`_dirty=True`）才写入
- **备份格式**: JSON（条目）+ NPY（向量矩阵）

### 恢复流程

```
启动 → 检查 META_FILE → 存在 → 加载 entries.json + vectors.npy → 完成
                      → 不存在 → 需要从数据库重建索引
```

## 故障降级流程

```
搜索请求
  │
  ├── 向量可用？ ──Yes──→ Full Mode (向量+关键词+重排)
  │                    │
  │                    └── 重排失败 → 降级到向量+关键词融合
  │
  └── 向量不可用？ ──→ Keyword Mode (倒排索引关键词搜索)
```
