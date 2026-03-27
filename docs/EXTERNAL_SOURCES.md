# 外部数据源接入方案

## 架构设计

```
用户搜索 → ClawRiver 内部搜索 → 结果不足？ → 外部数据源补充
                                          ↓
                                   Google Scholar
                                   arXiv
                                   GitHub
                                   知网/万方
```

## 核心 API

### 新增搜索端点

```
GET /api/v1/memories/search/unified?query=xxx&sources=internal,scholar,arxiv
```

返回结果增加 `source` 字段：
- `source: "internal"` — ClawRiver 内部记忆
- `source: "google_scholar"` — Google Scholar 论文
- `source: "arxiv"` — arXiv 预印本
- `source: "github"` — GitHub 代码/文档

## 外部数据源适配器

### 1. Google Scholar 适配器

```python
class GoogleScholarAdapter:
    """Google Scholar 学术论文搜索"""
    
    async def search(self, query: str, limit: int = 5) -> list:
        # 用 scholarly 库或直接爬取
        # 返回标准化格式
        return [{
            "source": "google_scholar",
            "title": "...",
            "authors": ["..."],
            "year": 2024,
            "citations": 45,
            "url": "https://scholar.google.com/...",
            "pdf_url": "https://...",  # 如果有开放获取PDF
            "abstract": "...",
            "price": 0,  # 外部资源免费展示摘要
        }]
```

### 2. arXiv 适配器

```python
class ArxivAdapter:
    """arXiv 预印本搜索（完全开放获取）"""
    
    async def search(self, query: str, limit: int = 5) -> list:
        # arXiv API: http://export.arxiv.org/api/query
        return [{
            "source": "arxiv",
            "title": "...",
            "authors": ["..."],
            "arxiv_id": "2401.12345",
            "url": "https://arxiv.org/abs/2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
            "abstract": "...",
            "categories": ["cs.AI", "cs.AR"],
        }]
```

### 3. GitHub 适配器

```python
class GitHubAdapter:
    """GitHub 仓库/文档搜索"""
    
    async def search(self, query: str, limit: int = 5) -> list:
        # GitHub Search API
        return [{
            "source": "github",
            "repo": "owner/repo",
            "description": "...",
            "stars": 1234,
            "url": "https://github.com/owner/repo",
            "file_url": "https://github.com/owner/repo/blob/main/README.md",
        }]
```

## 搜索逻辑

```python
async def unified_search(query: str, sources: list[str]) -> dict:
    """统一搜索：内部 + 外部"""
    
    results = []
    
    # 1. 内部搜索
    if "internal" in sources:
        internal = await search_memories(query)
        results.extend([{"source": "internal", **r} for r in internal])
    
    # 2. 内部结果不足时，补充外部
    if len(internal) < 3 and "scholar" in sources:
        scholar = await GoogleScholarAdapter().search(query)
        results.extend(scholar)
    
    if len(internal) < 3 and "arxiv" in sources:
        arxiv = await ArxivAdapter().search(query)
        results.extend(arxiv)
    
    # 3. 去重 + 排序
    return {"items": deduplicate(results), "sources_used": sources}
```

## MCP 工具扩展

```python
@mcp.tool(
    annotations={"title": "统一知识搜索", "readOnlyHint": True}
)
async def search_knowledge(
    query: str,
    sources: str = "internal,scholar,arxiv",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """搜索知识（内部记忆 + 外部学术资源）
    
    Args:
        query: 搜索关键词
        sources: 数据源，逗号分隔 (internal/scholar/arxiv/github)
        limit: 每个源返回数量
    """
    if ctx:
        await ctx.info(f"🔍 跨源搜索: {query}")
    
    result = await unified_search(query, sources.split(","), limit)
    
    if ctx:
        await ctx.info(f"✅ 找到 {len(result['items'])} 条结果")
    
    return result
```

## 前端展示

搜索结果按来源分组：

```
🔍 搜索: 高压直流 数据中心

📖 ClawRiver 内部 (2 条)
  • 数据中心供电系统架构
  • HVDC 效率优化

📄 Google Scholar (5 条)
  • [论文] Overview of VRMs in 48V data center (2022, 引用45)
  • [论文] Two-stage 48-V VRM optimization (2020, 引用144)

📝 arXiv (3 条)
  • [预印本] High-frequency DC-DC converter design (2024)
```

## 实施优先级

| 阶段 | 内容 | 工时 |
|------|------|------|
| P0 | arXiv 适配器（完全免费开放） | 2h |
| P1 | Google Scholar 适配器 | 3h |
| P2 | GitHub 适配器 | 1h |
| P3 | 统一搜索 API + MCP 工具 | 2h |
| P4 | 前端分组展示 | 2h |

## 依赖

```txt
# requirements.txt 添加
scholarly>=1.7    # Google Scholar
arxiv>=2.1        # arXiv API
PyGithub>=2.0     # GitHub API
```
