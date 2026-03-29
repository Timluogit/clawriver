"""外部数据源搜索"""
from .arxiv_adapter import ArxivAdapter, ArxivResult
from .openalex_adapter import OpenAlexAdapter
from .hackernews_adapter import HackerNewsAdapter
from .semantic_scholar_adapter import SemanticScholarAdapter
from .base import SearchResult

ALL_ADAPTERS = {
    "arxiv": ArxivAdapter(),
    "openalex": OpenAlexAdapter(),
    "hackernews": HackerNewsAdapter(),
    "semantic_scholar": SemanticScholarAdapter(),
}

async def search_external(query: str, sources: list[str] = None, limit: int = 5):
    """统一外部搜索，并发调用各数据源"""
    import asyncio
    if sources is None:
        sources = list(ALL_ADAPTERS.keys())
    tasks = []
    for src in sources:
        if src in ALL_ADAPTERS:
            tasks.append(ALL_ADAPTERS[src].search(query, max_results=limit))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged = []
    for r in results:
        if isinstance(r, list):
            merged.extend(r)
        elif isinstance(r, Exception):
            pass  # silently skip
    return merged

__all__ = ["ArxivAdapter", "ArxivResult", "SearchResult", "search_external", "ALL_ADAPTERS"]
