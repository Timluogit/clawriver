"""技术文档检索服务 — Agent 查文档专用"""
import httpx
from typing import Optional
import re


# 支持的文档源配置
DOC_SOURCES = {
    "python": {
        "name": "Python 官方文档",
        "search_url": "https://docs.python.org/3/search.html?q={query}",
        "base_url": "https://docs.python.org/3/",
        "lang": "python",
    },
    "mdn": {
        "name": "MDN Web Docs",
        "search_url": "https://developer.mozilla.org/en-US/search?q={query}",
        "base_url": "https://developer.mozilla.org/en-US/docs/",
        "lang": "javascript",
    },
    "fastapi": {
        "name": "FastAPI 文档",
        "search_url": "https://fastapi.tiangolo.com/search/?q={query}",
        "base_url": "https://fastapi.tiangolo.com/",
        "lang": "python",
    },
    "docker": {
        "name": "Docker 文档",
        "search_url": "https://docs.docker.com/search/?q={query}",
        "base_url": "https://docs.docker.com/",
        "lang": "devops",
    },
    "linux": {
        "name": "Linux Man Pages",
        "search_url": "https://man7.org/linux/man-pages/search.html?q={query}",
        "base_url": "https://man7.org/linux/man-pages/",
        "lang": "shell",
    },
    "pypi": {
        "name": "PyPI 包搜索",
        "search_url": "https://pypi.org/search/?q={query}",
        "base_url": "https://pypi.org/project/",
        "lang": "python",
    },
    "npm": {
        "name": "NPM 包搜索",
        "search_url": "https://www.npmjs.com/search?q={query}",
        "base_url": "https://www.npmjs.com/package/",
        "lang": "javascript",
    },
    "github": {
        "name": "GitHub 代码搜索",
        "search_url": "https://github.com/search?q={query}&type=code",
        "base_url": "https://github.com/",
        "lang": "all",
    },
}


def get_doc_sources():
    """获取所有可用文档源列表"""
    return {
        key: {"name": src["name"], "lang": src["lang"]}
        for key, src in DOC_SOURCES.items()
    }


async def search_docs(query: str, source: Optional[str] = None, limit: int = 5) -> dict:
    """
    搜索技术文档

    通过 SearXNG/Brave 搜索定向到文档站点，返回结构化结果
    """
    results = []

    # 确定搜索范围
    if source and source in DOC_SOURCES:
        sources = {source: DOC_SOURCES[source]}
    else:
        sources = DOC_SOURCES

    # 构建搜索查询：限定在文档站点
    for src_key, src_config in sources.items():
        site_filter = _extract_domain(src_config["base_url"])
        search_query = f"{query} site:{site_filter}"

        try:
            # 使用 DuckDuckGo HTML 搜索（免费、无需 API Key）
            items = await _search_ddg(search_query, limit=3)
            for item in items:
                item["source"] = src_key
                item["source_name"] = src_config["name"]
                results.append(item)
        except Exception:
            continue

    # 去重 + 按相关性排序
    seen_urls = set()
    unique_results = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique_results.append(r)

    return {
        "success": True,
        "query": query,
        "source": source or "all",
        "total": len(unique_results),
        "results": unique_results[:limit],
    }


async def _search_ddg(query: str, limit: int = 5) -> list:
    """通过 DuckDuckGo Lite 搜索"""
    url = "https://lite.duckduckgo.com/lite/"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DocSearch/1.0)"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, data={"q": query}, headers=headers)
        html = resp.text

    # 简单解析搜索结果
    results = []
    # 匹配搜索结果链接
    links = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>([^<]+)</a>', html)
    for href, title in links:
        if len(results) >= limit:
            break
        # 过滤掉 DuckDuckGo 自己的链接
        if "duckduckgo.com" in href:
            continue
        results.append({
            "title": title.strip(),
            "url": href,
            "snippet": "",
        })

    return results


def _extract_domain(url: str) -> str:
    """从 URL 提取域名"""
    match = re.match(r'https?://([^/]+)', url)
    return match.group(1) if match else url
