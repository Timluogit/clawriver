import httpx
from typing import List
from .base import SearchResult, BaseSearchAdapter


class SemanticScholarAdapter(BaseSearchAdapter):
    source_name: str = "semantic_scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "query": query,
                    "limit": max_results,
                    "fields": "title,authors,year,abstract,url,externalIds,citationCount"
                }
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print("Semantic Scholar rate limited, returning empty list")
            else:
                print(f"Semantic Scholar search failed: {e}")
            return []
        except Exception as e:
            print(f"Semantic Scholar search failed: {e}")
            return []

    def _parse_response(self, data: dict) -> List[SearchResult]:
        results = []
        for paper in data.get("data", []):
            title = paper.get("title", "")
            authors = [
                a.get("name", "")
                for a in paper.get("authors", [])
            ]
            summary = paper.get("abstract", "") or ""
            url = paper.get("url", "")
            if not url:
                external_ids = paper.get("externalIds", {})
                corpus_id = external_ids.get("CorpusId")
                if corpus_id:
                    url = f"https://www.semanticscholar.org/paper/{corpus_id}"
            published = str(paper.get("year", "")) if paper.get("year") else None
            extra = {"citationCount": paper.get("citationCount")}
            results.append(SearchResult(
                source=self.source_name,
                source_type="paper",
                title=title,
                authors=authors,
                summary=summary,
                url=url,
                published=published,
                extra=extra
            ))
        return results
