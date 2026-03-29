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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "url": self.url,
            "published": self.published,
            "extra": self.extra,
            "price": 0,
            "format_type": self.source_type,
        }


class BaseSearchAdapter(ABC):
    source_name: str = ""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 5, **kwargs) -> List[SearchResult]:
        pass
