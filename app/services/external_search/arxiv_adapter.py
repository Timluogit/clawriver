"""arXiv 外部数据源适配器"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArxivResult:
    """arXiv 搜索结果"""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published: str
    updated: str
    pdf_url: str
    abs_url: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": "arxiv",
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract[:200] + "..." if len(self.abstract) > 200 else self.abstract,
            "abstract_full": self.abstract,
            "categories": self.categories,
            "published": self.published,
            "pdf_url": self.pdf_url,
            "abs_url": self.abs_url,
            "doi": self.doi,
            "journal_ref": self.journal_ref,
            "price": 0,
            "format_type": "paper",
        }


class ArxivAdapter:
    """arXiv API 适配器

    arXiv API 文档: https://info.arxiv.org/help/api/index.html
    完全免费，无需 API Key
    """

    BASE_URL = "https://export.arxiv.org/api/query"

    async def search(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        categories: Optional[List[str]] = None,
    ) -> List[ArxivResult]:
        """搜索 arXiv 论文

        Args:
            query: 搜索关键词
            max_results: 最大返回数量
            sort_by: 排序方式
            sort_order: 排序顺序
            categories: 限定分类（可选）
        """
        search_query = f"all:{query}"
        if categories:
            cat_query = " OR ".join([f"cat:{c}" for c in categories])
            search_query = f"({search_query}) AND ({cat_query})"

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                return self._parse_response(resp.text)
        except Exception as e:
            print(f"arXiv 搜索失败: {e}")
            return []

    def _parse_response(self, xml_text: str) -> List[ArxivResult]:
        """解析 arXiv API XML 响应"""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        root = ET.fromstring(xml_text)
        results = []

        for entry in root.findall("atom:entry", ns):
            arxiv_id_url = entry.find("atom:id", ns).text
            arxiv_id = arxiv_id_url.split("/abs/")[-1]

            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")

            authors = [
                author.find("atom:name", ns).text
                for author in entry.findall("atom:author", ns)
            ]

            abstract = entry.find("atom:summary", ns).text.strip()

            categories = [
                cat.get("term")
                for cat in entry.findall("atom:category", ns)
            ]

            published = entry.find("atom:published", ns).text[:10]
            updated = entry.find("atom:updated", ns).text[:10]

            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            doi_elem = entry.find("arxiv:doi", ns)
            doi = doi_elem.text if doi_elem is not None else None

            journal_elem = entry.find("arxiv:journal_ref", ns)
            journal_ref = journal_elem.text if journal_elem is not None else None

            results.append(ArxivResult(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published=published,
                updated=updated,
                pdf_url=pdf_url,
                abs_url=f"https://arxiv.org/abs/{arxiv_id}",
                doi=doi,
                journal_ref=journal_ref,
            ))

        return results
