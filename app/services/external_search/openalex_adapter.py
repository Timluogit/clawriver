import httpx
from typing import List
from .base import SearchResult, BaseSearchAdapter


class OpenAlexAdapter(BaseSearchAdapter):
    source_name: str = "openalex"
    BASE_URL = "https://api.openalex.org/works"

    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "search": query,
                    "per_page": max_results,
                    "select": "title,publication_year,authorships,doi,primary_location,open_access"
                }
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data)
        except Exception as e:
            print(f"OpenAlex search failed: {e}")
            return []

    def _parse_response(self, data: dict) -> List[SearchResult]:
        results = []
        for work in data.get("results", []):
            title = work.get("title", "")
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in work.get("authorships", [])
            ]
            summary = ""  # OpenAlex doesn't provide abstracts in free tier
            url = work.get("doi", "")
            if not url:
                primary_location = work.get("primary_location", {})
                url = primary_location.get("landing_page_url", "")
            published = str(work.get("publication_year", "")) if work.get("publication_year") else None
            results.append(SearchResult(
                source=self.source_name,
                source_type="paper",
                title=title,
                authors=authors,
                summary=summary,
                url=url,
                published=published,
                extra={}
            ))
        return results
