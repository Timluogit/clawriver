"""Note Builder: constructs AgenticMemory from raw content."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
from sentence_transformers import SentenceTransformer

from amev_schema import AgenticMemory, LLMClient

if TYPE_CHECKING:
    pass


class NoteBuilder:
    """Builds structured AgenticMemory notes from raw interaction content.

    Combines LLM-based metadata extraction with sentence-transformer embeddings
    to produce a complete memory representation.

    Args:
        llm_client: LLM client implementing the LLMClient protocol.
        model_name: Sentence-transformer model name (default: all-MiniLM-L6-v2).

    Example:
        >>> from mock_llm import MockLLMClient
        >>> builder = NoteBuilder(MockLLMClient())
        >>> memory = builder.build("Python is great for machine learning")
        >>> memory.keywords
        ['python', 'is', 'great', 'for', 'machine']
    """

    def __init__(self, llm_client: LLMClient, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.llm_client = llm_client
        self._model_name = model_name
        self._embedder: SentenceTransformer | None = None

    @property
    def embedder(self) -> SentenceTransformer:
        """Lazy-load the sentence transformer model."""
        if self._embedder is None:
            self._embedder = SentenceTransformer(self._model_name)
        return self._embedder

    def build(self, content: str) -> AgenticMemory:
        """Construct a complete AgenticMemory from raw content.

        Pipeline:
            1. Call LLM to extract keywords, tags, and context description.
            2. Generate embedding vector via sentence-transformers.
            3. Assemble and return the AgenticMemory object.

        Args:
            content: Raw interaction text.

        Returns:
            Fully populated AgenticMemory instance.
        """
        # Step 1: LLM metadata extraction
        metadata = self.llm_client.extract_metadata(content)

        # Step 2: Generate embedding
        embedding = self._encode(content)

        # Step 3: Assemble memory
        return AgenticMemory(
            id=AgenticMemory.new_id(),
            content=content,
            timestamp=datetime.now(timezone.utc),
            keywords=metadata.keywords,
            tags=metadata.tags,
            context_desc=metadata.context_desc,
            embedding=embedding,
            links=[],
        )

    def _encode(self, text: str) -> np.ndarray:
        """Encode text to a normalized embedding vector.

        Args:
            text: Input text.

        Returns:
            L2-normalized numpy array of shape (384,).
        """
        vec = self.embedder.encode(text, normalize_embeddings=True)
        return np.array(vec, dtype=np.float32)
