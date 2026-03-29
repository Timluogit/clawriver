"""Mock LLM client for testing A-MEM without real API calls."""

from __future__ import annotations

from typing import List

from amev_schema import LLMMetadata


class MockLLMClient:
    """A deterministic mock LLM client for unit testing.

    Returns predictable outputs based on input content length and keywords.
    Useful for testing the A-MEM pipeline without API dependencies.

    Example:
        >>> client = MockLLMClient()
        >>> meta = client.extract_metadata("Python is great for AI")
        >>> meta.keywords
        ['python', 'great', 'ai']
    """

    def extract_metadata(self, content: str) -> LLMMetadata:
        """Extract mock metadata: lowercase words as keywords, simple tags."""
        words = content.lower().split()
        # Take unique words up to 5 as keywords
        keywords = list(dict.fromkeys(words))[:5]
        # Generate tags based on content length
        tags: list[str] = []
        if len(words) < 10:
            tags.append("short")
        else:
            tags.append("detailed")
        if "?" in content:
            tags.append("question")
        else:
            tags.append("statement")
        context_desc = f"Mock context: {content[:50]}..."
        return LLMMetadata(keywords=keywords, tags=tags, context_desc=context_desc)

    def evaluate_link(
        self,
        new_content: str,
        new_keywords: List[str],
        candidate_content: str,
        candidate_keywords: List[str],
    ) -> str:
        """Simple keyword overlap heuristic for link evaluation."""
        overlap = set(new_keywords) & set(candidate_keywords)
        return "YES" if len(overlap) >= 1 else "NO"

    def analyze_evolution(
        self,
        new_content: str,
        new_keywords: List[str],
        existing_content: str,
        existing_keywords: List[str],
        existing_tags: List[str],
    ) -> LLMMetadata | None:
        """Return updated metadata if keywords overlap, else None."""
        overlap = set(new_keywords) & set(existing_keywords)
        if len(overlap) >= 2:
            merged_keywords = list(
                dict.fromkeys(existing_keywords + new_keywords)
            )[:6]
            new_tags = list(set(existing_tags + ["evolved"]))
            return LLMMetadata(
                keywords=merged_keywords,
                tags=new_tags,
                context_desc=f"Evolved: {existing_content[:40]}... + {new_content[:30]}...",
            )
        return None
