# 向量语义搜索功能说明

## 概述

ClawRiver 现已支持向量语义搜索，使用 TF-IDF + 余弦相似度实现轻量级语义搜索能力。

## 特性

- **三种搜索模式**：
  - `keyword`: 传统关键词匹配搜索
  - `semantic`: 纯语义搜索（基于 TF-IDF 向量）
  - `hybrid`: 混合搜索（默认，结合语义和关键词）

- **性能优秀**：
  - 平均搜索延迟 < 2ms
  - 支持中英文搜索
  - 自动缓存向量索引

- **API 兼容**：
  - 完全向后兼容现有 API
  - 可选使用新功能

## 技术实现

### 核心组件

1. **app/search/vector_search.py**: 向量搜索引擎
   - 使用 sklearn 的 TF-IDF 向量化
   - 字符级 ngram 分析（支持中文）
   - 余弦相似度计算
   - 本地缓存优化

2. **app/services/memory_service.py**: 搜索服务集成
   - `_keyword_search()`: 关键词搜索
   - `_semantic_search()`: 语义搜索
   - `_hybrid_search()`: 混合搜索
   - `_execute_search()`: 通用搜索执行

### 搜索算法

#### TF-IDF 向量化
```python
TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 3),
    analyzer='char_wb',  # 字符级，支持中文
    sublinear_tf=True
)
```

#### 混合搜索权重
- 语义搜索权重: 60%
- 关键词匹配权重: 40%

## API 使用

### 搜索接口

```bash
GET /memories?search_type=hybrid&query=Python开发
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| search_type | string | hybrid | 搜索类型: keyword / semantic / hybrid |
| query | string | "" | 搜索关键词 |
| category | string | "" | 分类筛选 |
| format_type | string | "" | 格式筛选 |
| min_score | float | 0 | 最低评分 |
| max_price | int | 999999 | 最高价格（分） |
| page | int | 1 | 页码 |
| page_size | int | 10 | 每页数量 |
| sort_by | string | relevance | 排序方式 |

### 使用示例

#### 1. 语义搜索
```bash
curl "http://localhost:8000/memories?search_type=semantic&query=API开发&page_size=5"
```

#### 2. 关键词搜索（原有方式）
```bash
curl "http://localhost:8000/memories?search_type=keyword&query=Python&page_size=5"
```

#### 3. 混合搜索（推荐）
```bash
curl "http://localhost:8000/memories?search_type=hybrid&query=web安全&category=安全&page_size=5"
```

## 性能数据

基于测试结果（5条测试记忆，10次迭代）：

| 搜索类型 | 平均延迟 | 最小延迟 | 最大延迟 |
|----------|----------|----------|----------|
| keyword  | 0.88ms   | 0.77ms   | 1.54ms   |
| semantic | 1.27ms   | 1.22ms   | 1.36ms   |
| hybrid   | 1.43ms   | 1.41ms   | 1.49ms   |

**结论**: 所有模式均远低于 200ms 目标 ✓

## 部署说明

### 1. 安装依赖

```bash
pip install scikit-learn
```

或更新 requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. 缓存目录

默认缓存目录: `/tmp/memory_market_cache`

可通过 `VectorSearchEngine(cache_dir="...")` 自定义。

### 3. 缓存策略

- 自动缓存向量索引到本地文件
- 数据变更时自动更新索引
- 支持强制重建索引

## 最佳实践

### 1. 搜索模式选择

- **keyword**: 精确匹配场景（如已知关键词）
- **semantic**: 模糊搜索场景（如概念查询）
- **hybrid**: 通用场景（推荐，平衡准确性和召回率）

### 2. 查询优化

```python
# 好的查询：具体且有语义
"Python 异步编程实战"
"Web API 安全防护"

# 避免的查询：过于简短
"Python"
"API"
```

### 3. 组合筛选

```python
# 结合语义和筛选条件效果更好
query = "机器学习"
category = "AI/机器学习"
format_type = "tutorial"
```

## 测试

运行测试验证功能：

```bash
# 单元测试：向量搜索引擎
python test_semantic_search.py

# 集成测试：完整搜索流程
python test_search_integration.py
```

## 未来优化

### 可能的改进方向

1. **更高级的向量化**
   - 集成 sentence-transformers
   - 支持多语言模型（如 paraphrase-multilingual）

2. **向量数据库**
   - 集成 Qdrant（已有依赖）
   - 支持更大规模的向量索引

3. **智能权重调整**
   - 根据查询类型动态调整权重
   - 学习用户偏好

4. **查询扩展**
   - 同义词扩展
   - 自动纠错

## 故障排查

### 问题：语义搜索无结果

**原因**: 数据量太少或查询不匹配

**解决**:
- 增加记忆数量
- 使用更通用的查询词
- 尝试混合搜索模式

### 问题：性能下降

**原因**: 缓存失效或数据量过大

**解决**:
- 检查缓存目录权限
- 减少 max_features 参数
- 使用分页限制结果数量

## 贡献

欢迎提交问题和改进建议！
