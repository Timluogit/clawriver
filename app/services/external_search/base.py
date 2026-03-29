from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SearchResult:
    source: str          # "openalex" / "hackernews" / "semantic_scholar" / "arxiv"
    source_type: str     # "paper" / "article"
    title: str
    authors: List[str]
    summary: str
    url: str
    published: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseSearchAdapter(ABC):
    source_name: str = ""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResult]:
        pass
