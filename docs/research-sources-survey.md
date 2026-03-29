# ClawRiver 外部知识源扩展调研报告

> 调研日期：2026-03-29

## 一、API 可用性验证结果

### 1.1 学术论文类

#### ✅ OpenAlex API — **推荐优先级：P0**
- **状态：完全可用，无需 API Key**
- **响应示例：** 搜索 "transformer" 返回 939,866 条结果，77ms 响应
- **返回字段：** title, doi, publication_year, authors (含 orcid), open_access 状态, source, citation 数等
- **费用：免费，无需注册**
- **速率限制：** 10 req/s (polite pool)，可申请加至 100 req/s
- **覆盖范围：** 2.5亿+ 学术论文，全学科

#### ⚠️ Semantic Scholar API — **推荐优先级：P1**
- **状态：可用，但有速率限制**
- **无 Key 测试：** 返回 `429 Too Many Requests`（共享 IP 池易被限流）
- **有 API Key 后：** 可获得更高限额，返回 title, authors, year, citationCount, url 等字段
- **费用：免费，API Key 免费申请**
- **速率限制：** 无 Key: ~100 req/5min；有 Key: 1 req/s (可申请更高)
- **覆盖范围：** 2亿+ 论文，含引用关系图谱（独特优势）

#### ✅ PubMed E-utilities — **推荐优先级：P1（医学/生命科学）**
- **状态：完全可用，无需 API Key**
- **响应示例：** 搜索 "CRISPR" 返回 65,822 条，含 PMID 列表
- **费用：免费**
- **速率限制：** 无 Key: 3 req/s；有 Key: 10 req/s
- **覆盖范围：** 3600万+ 生物医学文献
- **局限：** 仅生物医学领域

#### ❌ CORE API — **推荐优先级：P3（可选）**
- **状态：需要 API Key**
- **无 Key 测试：** 返回 401 重定向，无 Key 无法使用
- **有 API Key：** 免费，需注册申请
- **速率限制：** 有 Key: 10,000 req/month
- **覆盖范围：** 2亿+ 开放获取论文
- **评价：** 功能与 OpenAlex 重叠，且需注册，优先级低

### 1.2 专利类

#### ❌ Google Patents — **不可直接 API 调用**
- **状态：无官方公开 API**
- **替代方案：** 可用 web_fetch 抓取搜索页面（不稳定，不推荐生产环境）

#### ❌ USPTO PatentsView API — **推荐优先级：P2**
- **状态：测试返回 `{"detail":"You do not have permission to perform this action."}`
- **原因：** 可能需要注册或 IP 白名单
- **费用：免费**
- **覆盖范围：** 美国专利

#### ❌ Espacenet OPS API — **不可用**
- **状态：返回 403 Forbidden**
- **原因：** 需要注册获取 API Key，且审核严格
- **费用：免费，但审核流程复杂**

#### 💡 专利搜索替代方案：Google Patents Public Data (BigQuery)
- Google 提供公开 BigQuery 数据集，可通过 SQL 查询全球专利
- 但需要 GCP 项目和 BigQuery 配额，不适合轻量集成

**结论：专利搜索短期内难以免费集成，建议作为 V2 功能。**

### 1.3 技术文章类

#### ✅ Hacker News Algolia API — **推荐优先级：P0**
- **状态：完全可用，无需 API Key**
- **响应示例：** 返回 title, author, url, points, num_comments, created_at 等
- **费用：免费**
- **速率限制：** 无严格限制，建议 <1000 req/hour
- **覆盖范围：** Hacker News 全部帖子（科技/创业/AI）

#### ✅ dev.to API — **推荐优先级：P1**
- **状态：完全可用，无需 API Key**
- **响应示例：** 返回 title, description, url, tags, reading_time, reactions 等
- **费用：免费**
- **速率限制：** 无 Key: 100 req/hour；有 Key: 1000 req/hour
- **覆盖范围：** dev.to 社区文章

#### ❌ Medium API — **不可用**
- **状态：Medium 已于 2024 年关闭公开 API**
- **无替代方案**

## 二、现有系统集成分析

### 2.1 适配器接口规范

现有 `ArxivAdapter` 的模式：
1. **数据类：** `ArxivResult` (dataclass)，含 `to_dict()` 方法
2. **适配器类：** `ArxivAdapter`，实现 `async search()` 方法
3. **输出格式：** `to_dict()` 返回包含 `source`, `format_type`, `price`, `title`, `authors`, `abstract`, `pdf_url` 等标准字段

### 2.2 调用链路

```
API Layer (unified_search.py)
  → sources 参数指定数据源 ("internal,arxiv")
  → asyncio.gather 并发调用各适配器
  → 结果合并返回

独立调用 (external_search.py)
  → ExternalSearchEngine.search()
  → 通过 external_source_service._adapters[source_id].search()
  → 包含缓存、评分、过滤逻辑
```

### 2.3 新适配器集成方式

**方式 A（推荐）：扩展 unified_search API**
- 在 `unified_search.py` 的 `sources` 参数中增加新数据源
- 创建对应适配器（遵循 ArxivAdapter 模式）
- 零架构改动，纯增量

**方式 B：注册到 external_source_service**
- 通过管理后台动态启用/禁用数据源
- 更灵活但改动更大

## 三、推荐方案

### 3.1 第一阶段（V1）— 1-2 天开发量

| 数据源 | 类型 | API Key | 优先级 |
|--------|------|---------|--------|
| **OpenAlex** | 全学科论文 | 不需要 | P0 |
| **Hacker News** | 技术文章 | 不需要 | P0 |
| **Semantic Scholar** | 引用关系 | 免费申请 | P1 |

这三个 API 全部免费、无需/易获取 Key，覆盖论文+技术文章两大类。

### 3.2 第二阶段（V2）— 1 天开发量

| 数据源 | 类型 | API Key | 优先级 |
|--------|------|---------|--------|
| **PubMed** | 生物医学 | 不需要 | P1 |
| **dev.to** | 技术文章 | 不需要 | P1 |

### 3.3 第三阶段（V2+）— 待定

| 数据源 | 类型 | 难度 | 说明 |
|--------|------|------|------|
| 专利搜索 | 专利 | 高 | 无免费可用 API，需评估替代方案 |
| Medium | 技术文章 | - | API 已关闭 |

### 3.4 集成方案设计

```
app/services/external_search/
  ├── __init__.py          # 导出所有适配器
  ├── base.py              # 抽象基类 (新增)
  ├── arxiv_adapter.py     # 现有
  ├── openalex_adapter.py  # 新增
  ├── semantic_scholar_adapter.py  # 新增
  ├── hackernews_adapter.py        # 新增
  ├── pubmed_adapter.py    # 新增 (V2)
  └── devto_adapter.py     # 新增 (V2)
```

**统一接口：**
```python
class BaseSearchAdapter(ABC):
    source_name: str  # "openalex", "hackernews" 等
    
    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResultItem]:
        ...
```

**统一结果格式：**
```python
@dataclass
class SearchResultItem:
    source: str           # "openalex"
    source_type: str      # "paper" / "article" / "patent"
    title: str
    authors: List[str]
    summary: str          # 摘要或描述
    url: str              # 链接
    published: Optional[str]
    extra: Dict           # 源特有字段
    price: float = 0      # ClawRiver 统一价格字段
```

### 3.5 开发工作量估算

| 任务 | 工时 |
|------|------|
| 抽取 BaseSearchAdapter + 统一结果类 | 1h |
| OpenAlex 适配器 | 2h |
| Semantic Scholar 适配器 | 1.5h |
| Hacker News 适配器 | 1h |
| unified_search.py 集成 | 1h |
| 测试 + 错误处理 | 1h |
| **V1 合计** | **7.5h (~1天)** |

| PubMed 适配器 | 1.5h |
| dev.to 适配器 | 1h |
| **V2 合计** | **2.5h** |

## 四、总结

- **论文搜索**：OpenAlex 是最佳选择（免费、全学科、无需 Key、数据丰富），可完全替代 arXiv 的局限性
- **技术文章**：Hacker News + dev.to 组合覆盖主要开发者社区
- **专利搜索**：短期内无免费可用方案，建议暂缓
- **集成成本**：V1 约 1 天开发，纯增量改动，不影响现有功能
