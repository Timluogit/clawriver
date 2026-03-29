"""A-MEM Agentic Memory data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Protocol, runtime_checkable

import numpy as np


@dataclass
class AgenticMemory:
    """A single agentic memory note in the Zettelkasten-inspired A-MEM system.

    Each memory represents a structured interaction record that can evolve
    over time as new related memories are added.

    Attributes:
        id: Unique identifier (c_i).
        content: Raw interaction content (original text).
        timestamp: Creation time (t_i).
        keywords: LLM-extracted keywords (K_i).
        tags: LLM-assigned semantic tags (G_i).
        context_desc: LLM-generated contextual description (X_i).
        embedding: Dense vector representation (e_i), 384-dim for all-MiniLM-L6-v2.
        links: IDs of related memories (L_i).
    """

    id: str
    content: str
    timestamp: datetime
    keywords: List[str]
    tags: List[str]
    context_desc: str
    embedding: np.ndarray
    links: List[str] = field(default_factory=list)

    @staticmethod
    def new_id() -> str:
        """Generate a new unique memory ID."""
        return uuid.uuid4().hex[:12]

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict (embedding as list)."""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "keywords": self.keywords,
            "tags": self.tags,
            "context_desc": self.context_desc,
            "embedding": self.embedding.tolist(),
            "links": self.links,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgenticMemory:
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            keywords=data["keywords"],
            tags=data["tags"],
            context_desc=data["context_desc"],
            embedding=np.array(data["embedding"], dtype=np.float32),
            links=data.get("links", []),
        )


@dataclass
class LLMMetadata:
    """Metadata extracted by LLM from raw content.

    Attributes:
        keywords: Key terms extracted from the content.
        tags: Semantic category tags.
        context_desc: A concise contextual summary.
    """

    keywords: List[str]
    tags: List[str]
    context_desc: str


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients used by A-MEM components.

    Any object implementing these two methods can serve as the LLM backend.
    This enables easy mocking in tests and swapping between providers.
    """

    def extract_metadata(self, content: str) -> LLMMetadata:
        """Extract keywords, tags, and context description from content.

        Args:
            content: Raw text content to analyze.

        Returns:
            LLMMetadata with extracted fields.
        """
        ...

    def evaluate_link(
        self, new_content: str, new_keywords: List[str],
        candidate_content: str, candidate_keywords: List[str],
    ) -> str:
        """Determine if two memories should be linked.

        Args:
            new_content: Content of the new memory.
            new_keywords: Keywords of the new memory.
            candidate_content: Content of the candidate linked memory.
            candidate_keywords: Keywords of the candidate linked memory.

        Returns:
            "YES" if they should be linked, "NO" otherwise.
        """
        ...

    def analyze_evolution(
        self, new_content: str, new_keywords: List[str],
        existing_content: str, existing_keywords: List[str],
        existing_tags: List[str],
    ) -> LLMMetadata | None:
        """Analyze how a new memory should affect an existing memory.

        Args:
            new_content: Content of the newly added memory.
            new_keywords: Keywords of the new memory.
            existing_content: Content of the existing memory.
            existing_keywords: Keywords of the existing memory.
            existing_tags: Tags of the existing memory.

        Returns:
            Updated LLMMetadata if the existing memory should evolve,
            or None if no changes are needed.
        """
        ...
