import httpx
from typing import List
from .base import SearchResult, BaseSearchAdapter


class HackerNewsAdapter(BaseSearchAdapter):
    source_name: str = "hackernews"
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "query": query,
                    "tags": "story",
                    "hitsPerPage": max_results
                }
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data)
        except Exception as e:
            print(f"HackerNews search failed: {e}")
            return []

    def _parse_response(self, data: dict) -> List[SearchResult]:
        results = []
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            authors = [hit.get("author", "")] if hit.get("author") else []
            summary = hit.get("story_text", "") or ""
            url = hit.get("url", "")
            if not url:
                object_id = hit.get("objectID", "")
                url = f"https://news.ycombinator.com/item?id={object_id}"
            published = hit.get("created_at", "")
            results.append(SearchResult(
                source=self.source_name,
                source_type="article",
                title=title,
                authors=authors,
                summary=summary,
                url=url,
                published=published,
                extra={}
            ))
        return results
