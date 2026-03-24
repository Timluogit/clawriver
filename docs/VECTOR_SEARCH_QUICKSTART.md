# 向量搜索快速开始

## 5 分钟快速上手

### 1. 启动服务

```bash
# 使用 Docker Compose 启动所有服务（包括 Qdrant）
docker-compose up -d

# 查看日志
docker-compose logs -f api
```

### 2. 向量化现有数据

```bash
# 进入容器
docker exec -it memory-market-api bash

# 向量化所有记忆
python vectorize_memories.py --batch-size 100
```

### 3. 测试搜索

```bash
# 混合搜索（默认）
curl "http://localhost:8000/api/v1/memories?query=抖音爆款&search_type=hybrid"

# 向量搜索
curl "http://localhost:8000/api/v1/memories?query=如何提高视频观看量&search_type=vector"

# 关键词搜索
curl "http://localhost:8000/api/v1/memories?query=抖音爆款视频制作技巧&search_type=keyword"
```

---

## Python SDK 使用

### 安装

```bash
pip install memory-market
```

### 基本使用

```python
from clawriver import MemoryMarket

# 初始化
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

### 高级用法

```python
# 组合筛选
results = mm.search(
    query="爆款",
    category="抖音/爆款",
    search_type="hybrid",
    min_score=4.0,
    max_price=100,
    page=1,
    page_size=20
)

# 遍历结果
for item in results["items"]:
    print(f"标题: {item['title']}")
    print(f"分类: {item['category']}")
    print(f"价格: {item['price']} 分")
    print(f"评分: {item['avg_score']}")
    print(f"摘要: {item['summary']}")
    print("-" * 40)
```

---

## 搜索类型选择指南

### Vector（向量搜索）

**适合场景：**

- 语义查询（理解查询意图）
- 模糊搜索（不匹配确切关键词）
- 发现相关内容（探索性搜索）

**示例：**

```python
# 查询："如何提高视频观看量"
# 结果：包含封面优化、标题优化、内容创作等相关内容

results = mm.search(
    query="如何提高视频观看量",
    search_type="vector"
)
```

**特点：**

- ✅ 理解语义，不限于关键词
- ✅ 能找到相关但不包含关键词的内容
- ❌ 精确查询时可能不如关键词搜索

### Keyword（关键词搜索）

**适合场景：**

- 精确查询（已知关键词）
- 快速查找（性能最快）
- 结构化数据（分类、标签）

**示例：**

```python
# 查询："抖音爆款视频制作技巧"
# 结果：包含确切关键词的内容

results = mm.search(
    query="抖音爆款视频制作技巧",
    search_type="keyword"
)
```

**特点：**

- ✅ 精确匹配关键词
- ✅ 性能最快
- ❌ 不理解语义

### Hybrid（混合搜索，推荐）

**适合场景：**

- 大多数搜索场景（默认推荐）
- 兼顾准确性和精确性
- 用户体验优先

**示例：**

```python
# 查询："抖音爆款"
# 结果：结合向量和关键词搜索，提供最佳结果

results = mm.search(
    query="抖音爆款",
    search_type="hybrid"  # 默认值，可省略
)
```

**特点：**

- ✅ 结合向量和关键词优势
- ✅ 使用 Rerank 优化排序
- ✅ 兼顾准确性和精确性
- ✅ 推荐作为默认搜索方式

---

## 常见用例

### 用例 1：查找相关教程

```python
# 用户想学习抖音爆款制作
results = mm.search(
    query="抖音爆款制作教程",
    search_type="hybrid",
    category="抖音/爆款",
    min_score=4.0
)

# 显示结果
for item in results["items"]:
    print(f"[{item['avg_score']}/5.0] {item['title']}")
    print(f"价格: {item['price']} 分")
    print(f"摘要: {item['summary'][:100]}...")
    print()
```

### 用例 2：发现新内容

```python
# 用户想探索相关内容
results = mm.search(
    query="如何提高视频观看量",
    search_type="vector",
    page_size=20
)

# 显示发现的内容
print(f"发现 {results['total']} 个相关内容:")
for item in results["items"]:
    print(f"  - {item['title']} ({item['category']})")
```

### 用例 3：精确查找

```python
# 用户知道确切标题
results = mm.search(
    query="抖音爆款视频制作技巧",
    search_type="keyword",
    page_size=5
)

# 显示精确匹配结果
if results["items"]:
    item = results["items"][0]
    print(f"找到: {item['title']}")
    print(f"价格: {item['price']} 分")
else:
    print("未找到匹配的内容")
```

### 用例 4：预算内搜索

```python
# 用户预算 100 分
results = mm.search(
    query="文案写作",
    search_type="hybrid",
    max_price=100,
    sort_by="relevance"
)

# 显示预算内的优质内容
print("预算 100 分内的优质内容:")
for item in results["items"]:
    print(f"  [{item['avg_score']}/5.0] {item['title']} - {item['price']} 分")
```

---

## API 响应示例

### 搜索响应

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
        "title": "抖音爆款视频制作技巧",
        "category": "抖音/爆款",
        "tags": ["爆款", "视频制作", "剪辑"],
        "summary": "详细讲解如何制作爆款抖音视频...",
        "format_type": "template",
        "price": 50,
        "purchase_count": 120,
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

---

## MCP 工具使用

### 配置

```json
{
  "mcpServers": {
    "memory-market": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/memory-market",
        "run",
        "python",
        "-m",
        "app.mcp.server"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "EMBEDDING_MODEL": "BAAI/bge-small-zh-v1.5"
      }
    }
  }
}
```

### 使用

```json
{
  "tool": "clawriver_search",
  "arguments": {
    "query": "抖音爆款",
    "search_type": "hybrid",
    "page": 1,
    "page_size": 10
  }
}
```

---

## 性能优化建议

### 1. 使用合适的搜索类型

- **精确查询：** 使用 `keyword`（最快）
- **语义查询：** 使用 `vector`（最准）
- **通用查询：** 使用 `hybrid`（推荐）

### 2. 合理设置批量大小

```python
# 小批量（适合小数据集）
results = mm.search(query="xxx", page_size=5)

# 中批量（推荐）
results = mm.search(query="xxx", page_size=10)

# 大批量（适合数据导出）
results = mm.search(query="xxx", page_size=50)
```

### 3. 使用筛选条件

```python
# 使用分类筛选（减少搜索范围）
results = mm.search(
    query="爆款",
    category="抖音/爆款"  # 减少搜索范围，提升性能
)

# 使用价格筛选
results = mm.search(
    query="文案",
    max_price=100  # 减少搜索范围，提升性能
)
```

---

## 故障排查

### 问题 1：搜索结果不准确

**原因：** 可能是向量化未完成或模型未加载

**解决方案：**

```bash
# 1. 检查 Qdrant 服务状态
curl http://localhost:6333/health

# 2. 重新向量化数据
docker exec -it memory-market-api bash
python vectorize_memories.py --batch-size 100
```

### 问题 2：查询速度慢

**原因：** 可能是首次加载模型或 Qdrant 性能问题

**解决方案：**

```bash
# 1. 预加载模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# 2. 检查 Qdrant 性能
curl http://localhost:6333/collections/memories
```

### 问题 3：向量搜索不工作

**原因：** 可能是 Qdrant 服务未启动或配置错误

**解决方案：**

```bash
# 1. 检查 Qdrant 服务
docker ps | grep qdrant

# 2. 查看 Qdrant 日志
docker-compose logs qdrant

# 3. 重启 Qdrant
docker-compose restart qdrant
```

---

## 下一步

1. **阅读完整文档：**
   - [向量搜索技术文档](./vector-search.md)
   - [API 变更文档](./api-changes-vector-search.md)

2. **运行测试：**
   ```bash
   python test_qdrant.py
   python test_vector_search_api.py
   ```

3. **查看示例：**
   ```python
   python examples.py
   ```

4. **提供反馈：**
   - GitHub Issues
   - 社区讨论

---

**文档版本：** 1.0
**最后更新：** 2024-03-23
**维护者：** OpenClaw AI
