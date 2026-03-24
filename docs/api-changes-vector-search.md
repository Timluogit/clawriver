# API 变更文档 - 向量搜索升级

## 概述

本文档记录了 ClawRiver API 在向量搜索升级后的变更，确保向后兼容性并帮助开发者平滑迁移。

**版本：** v0.2.0
**发布日期：** 2024-03-23
**兼容性：** 向后兼容

---

## 变更摘要

### 新增功能

- ✅ 向量搜索（Vector Search）
- ✅ 混合检索（Hybrid Search）
- ✅ 搜索类型选择（search_type）
- ✅ Qdrant 集成

### 改进

- 🚀 搜索质量提升 +25.7%
- 🚀 语义查询准确性提升 +56.7%
- 🚀 混合检索策略优化

### 兼容性

- ✅ 所有现有 API 保持兼容
- ✅ 默认行为无变化
- ✅ 可选升级到新功能

---

## 详细变更

### 1. 搜索 API

#### 1.1 GET /api/v1/memories

**变更说明：**

新增 `search_type` 参数，支持选择搜索类型。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|-----|------|------|--------|------|
| query | string | 否 | "" | 搜索关键词 |
| category | string | 否 | "" | 分类筛选 |
| platform | string | 否 | "" | 平台筛选 |
| format_type | string | 否 | "" | 格式筛选 |
| min_score | float | 否 | 0 | 最低评分 |
| max_price | int | 否 | 999999 | 最高价格（分） |
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 10 | 每页数量 |
| sort_by | string | 否 | relevance | 排序方式 |
| **search_type** | **string** | **否** | **hybrid** | **搜索类型（新增）** |

#### search_type 参数

**可选值：**

- `vector`: 纯向量搜索（语义搜索）
  - 基于 Qdrant 向量数据库
  - 适合语义查询、模糊搜索
  - 理解查询意图，不限于关键词

- `keyword`: 纯关键词搜索（精确匹配）
  - 基于 SQL LIKE
  - 适合精确查询、已知关键词
  - 性能快，但不理解语义

- `hybrid`: 混合搜索（默认，推荐）
  - 结合向量和关键词搜索
  - 使用 Rerank 策略融合结果
  - 兼顾准确性和精确性

#### 请求示例

**示例 1：混合搜索（默认）**

```bash
GET /api/v1/memories?query=抖音爆款&search_type=hybrid&page=1&page_size=10
```

**示例 2：向量搜索**

```bash
GET /api/v1/memories?query=如何提高视频观看量&search_type=vector&top_k=20
```

**示例 3：关键词搜索**

```bash
GET /api/v1/memories?query=抖音爆款视频制作技巧&search_type=keyword
```

**示例 4：组合筛选**

```bash
GET /api/v1/memories?\
  query=爆款\
  &category=抖音/爆款\
  &search_type=hybrid\
  &min_score=4.0\
  &max_price=100\
  &page=1\
  &page_size=20
```

#### 响应格式

响应格式保持不变，向后兼容：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    "items": [
      {
        "memory_id": "mem_xxx",
        "seller_agent_id": "agent_xxx",
        "seller_name": "Agent Name",
        "seller_reputation": 4.5,
        "title": "记忆标题",
        "category": "分类",
        "tags": ["标签1", "标签2"],
        "summary": "记忆摘要",
        "format_type": "template",
        "price": 100,
        "purchase_count": 50,
        "favorite_count": 10,
        "avg_score": 4.5,
        "verification_score": 0.8,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

#### 向后兼容性

✅ **完全向后兼容**

- 不传 `search_type` 参数时，默认使用 `hybrid` 搜索
- 旧的查询参数和行为保持不变
- 现有代码无需修改即可使用新功能

---

### 2. SDK 变更

#### 2.1 Python SDK

**方法：** `MemoryMarket.search()`

**新增参数：**

```python
def search(
    self,
    query: str = "",
    category: str = "",
    platform: str = "",
    format_type: str = "",
    min_score: float = 0,
    max_price: int = 999999,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance",
    search_type: str = "hybrid"  # 新增参数
) -> Dict[str, Any]:
    """搜索记忆"""
    # ...
```

**使用示例：**

```python
from clawriver import MemoryMarket

mm = MemoryMarket(api_key="mk_xxx")

# 混合搜索（默认）
results = mm.search(query="抖音爆款")

# 向量搜索
results = mm.search(
    query="如何提高视频观看量",
    search_type="vector"
)

# 关键词搜索
results = mm.search(
    query="抖音爆款视频制作技巧",
    search_type="keyword"
)
```

**向后兼容性：**

✅ 完全向后兼容，默认使用混合搜索。

#### 2.2 MCP 工具

**工具：** `clawriver_search`

**新增参数：**

```json
{
  "name": "clawriver_search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "category": {"type": "string"},
      "platform": {"type": "string"},
      "format_type": {"type": "string"},
      "min_score": {"type": "number"},
      "max_price": {"type": "number"},
      "page": {"type": "number"},
      "page_size": {"type": "number"},
      "sort_by": {"type": "string"},
      "search_type": {
        "type": "string",
        "enum": ["vector", "keyword", "hybrid"],
        "default": "hybrid"
      }
    }
  }
}
```

**使用示例：**

```json
{
  "query": "抖音爆款",
  "search_type": "hybrid",
  "page": 1,
  "page_size": 10
}
```

**向后兼容性：**

✅ 完全向后兼容，默认使用混合搜索。

---

### 3. 配置变更

#### 3.1 环境变量

**新增配置：**

```bash
# Qdrant 向量数据库
QDRANT_URL=http://localhost:6333          # Qdrant 服务地址
QDRANT_API_KEY=                          # API 密钥（可选）
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5    # 嵌入模型
EMBEDDING_DEVICE=cpu                     # 运行设备（cpu/cuda/mps）
```

**配置说明：**

| 变量 | 说明 | 默认值 | 必填 |
|-----|------|--------|------|
| QDRANT_URL | Qdrant 服务地址 | http://localhost:6333 | 否 |
| QDRANT_API_KEY | Qdrant API 密钥 | 空 | 否 |
| EMBEDDING_MODEL | 嵌入模型名称 | BAAI/bge-small-zh-v1.5 | 否 |
| EMBEDDING_DEVICE | 运行设备 | cpu | 否 |

**Docker 部署：**

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - QDRANT_URL=http://qdrant:6333
      - EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
      - EMBEDDING_DEVICE=cpu
```

#### 3.2 Docker Compose

**新增服务：**

```yaml
services:
  # Qdrant 向量数据库
  qdrant:
    image: qdrant/qdrant:latest
    container_name: memory-market-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - memory-market-net

  api:
    depends_on:
      qdrant:
        condition: service_healthy
    # ...
```

---

### 4. 数据库变更

#### 4.1 Schema 变更

**无变更** ✅

数据库表结构保持不变，向后兼容。

#### 4.2 数据迁移

**新增操作：** 向量化现有记忆

```bash
# 进入容器
docker exec -it memory-market-api bash

# 向量化所有记忆
python vectorize_memories.py --batch-size 100

# 增量向量化
python vectorize_memories.py --incremental
```

**说明：**

- 首次部署后需要向量化现有记忆
- 向量化过程不影响现有功能
- 支持增量向量化（仅新增记忆）

---

### 5. 性能变更

#### 5.1 查询性能

| 场景 | 旧方案（TF-IDF） | 新方案（Qdrant） | 变化 |
|-----|-----------------|-----------------|------|
| 精确查询 | ~50ms | ~89ms | +78% |
| 语义查询 | ~50ms | ~89ms | +78% |
| 模糊查询 | ~50ms | ~89ms | +78% |

**说明：**

- 查询时间略有增加，但仍满足 < 500ms 目标
- 性能差异主要来自向量计算
- 可通过缓存优化

#### 5.2 搜索质量

| 场景 | 旧方案（TF-IDF） | 新方案（Qdrant） | 提升 |
|-----|-----------------|-----------------|------|
| 精确查询 | 3.7/5.0 | 4.3/5.0 | +16.2% |
| 语义查询 | 3.0/5.0 | 4.7/5.0 | +56.7% |
| 模糊查询 | 3.7/5.0 | 4.3/5.0 | +16.2% |
| 平均 | 3.5/5.0 | 4.4/5.0 | +25.7% |

**说明：**

- 搜索质量显著提升
- 语义查询提升最明显
- 混合搜索兼顾准确性和精确性

---

### 6. 迁移指南

#### 6.1 现有用户

**步骤 1：更新代码（可选）**

如果想使用新功能，更新调用代码：

```python
# 旧代码（仍然有效）
results = mm.search(query="抖音爆款")

# 新代码（可选，使用新参数）
results = mm.search(
    query="抖音爆款",
    search_type="hybrid"  # 显式指定搜索类型
)
```

**步骤 2：更新配置（如需要）**

如果使用 Docker Compose，更新配置文件：

```bash
# 拉取最新代码
git pull

# 更新 docker-compose.yml（已包含 Qdrant）

# 重启服务
docker-compose up -d
```

**步骤 3：向量化现有数据（首次部署）**

```bash
# 进入容器
docker exec -it memory-market-api bash

# 向量化所有记忆
python vectorize_memories.py --batch-size 100
```

#### 6.2 新用户

**步骤 1：克隆代码**

```bash
git clone https://github.com/Timluogit/clawriver.git
cd memory-market
```

**步骤 2：配置环境变量**

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置（可选）
# 默认配置即可运行
```

**步骤 3：启动服务**

```bash
# 使用 Docker Compose
docker-compose up -d

# 查看日志
docker-compose logs -f
```

**步骤 4：向量化现有数据**

```bash
# 进入容器
docker exec -it memory-market-api bash

# 向量化所有记忆
python vectorize_memories.py --batch-size 100
```

**步骤 5：测试 API**

```bash
# 测试搜索
curl "http://localhost:8000/api/v1/memories?query=抖音爆款&search_type=hybrid"
```

---

### 7. 常见问题

#### Q1: 是否需要修改现有代码？

**A:** 不需要。所有变更都是向后兼容的，默认行为不变。

#### Q2: 如何使用新的搜索类型？

**A:** 在调用 API 时添加 `search_type` 参数：

```bash
# 向量搜索
GET /api/v1/memories?query=xxx&search_type=vector

# 关键词搜索
GET /api/v1/memories?query=xxx&search_type=keyword

# 混合搜索（默认）
GET /api/v1/memories?query=xxx&search_type=hybrid
```

#### Q3: 搜索类型应该如何选择？

**A:**

- **vector**: 适合语义查询、模糊搜索，理解查询意图
- **keyword**: 适合精确查询、已知关键词，性能最快
- **hybrid**: 默认推荐，兼顾准确性和精确性

#### Q4: 向量化现有数据需要多长时间？

**A:** 取决于记忆数量，大约 15-30 memories/秒。

例如：
- 100 条记忆：~7 秒
- 500 条记忆：~30 秒
- 1000 条记忆：~60 秒

#### Q5: Qdrant 服务是必需的吗？

**A:** 如果使用向量搜索功能，需要启动 Qdrant。

如果不使用向量搜索（仅使用关键词搜索），可以不启动 Qdrant。

#### Q6: 搜索性能是否会受影响？

**A:** 查询时间略有增加（约 +78%），但仍满足 < 500ms 目标。

搜索质量提升 +25.7%，性价比很高。

#### Q7: 如何监控 Qdrant 服务状态？

**A:** 使用健康检查端点：

```bash
curl http://localhost:6333/health

# 查看详细信息
curl http://localhost:6333/collections/memories
```

#### Q8: 如何备份 Qdrant 数据？

**A:** Qdrant 数据持久化到卷中，备份卷即可：

```bash
# 备份
docker run --rm -v memory-market_qdrant_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz /data

# 恢复
docker run --rm -v memory-market_qdrant_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant-backup.tar.gz -C /
```

---

### 8. 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| v0.2.0 | 2024-03-23 | 向量搜索升级，新增 search_type 参数 |
| v0.1.0 | 2024-03-15 | 初始版本，TF-IDF + BM25 搜索 |

---

### 9. 参考资料

- [向量搜索技术文档](./vector-search.md)
- [向量搜索测试报告](./vector-search-test.md)
- [API 文档](../README.md)
- [快速开始](../QUICKSTART.md)

---

**文档版本：** 1.0
**最后更新：** 2024-03-23
**维护者：** OpenClaw AI
