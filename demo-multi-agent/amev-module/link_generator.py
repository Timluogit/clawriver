"""Link Generator: discovers semantic relationships between memories."""

from __future__ import annotations

from typing import List

import numpy as np

from amev_schema import AgenticMemory, LLMClient


class LinkGenerator:
    """Generates bidirectional links between memories using a two-stage approach.

    Stage 1 — Vector Retrieval:
        Compute cosine similarity between the new memory's embedding and all
        existing memories. Select top-k candidates.

    Stage 2 — LLM Evaluation:
        For each candidate, ask the LLM whether a meaningful semantic link
        exists. Only confirmed candidates are linked.

    Args:
        llm_client: LLM client implementing the LLMClient protocol.

    Example:
        >>> from mock_llm import MockLLMClient
        >>> gen = LinkGenerator(MockLLMClient())
        >>> # After building memories, call generate_links(...)
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_links(
        self,
        new_memory: AgenticMemory,
        memory_store: List[AgenticMemory],
        top_k: int = 5,
    ) -> List[str]:
        """Find and confirm semantic links for a new memory.

        Args:
            new_memory: The newly created memory to find links for.
            memory_store: All existing memories in the store.
            top_k: Maximum number of candidate memories to consider.

        Returns:
            List of memory IDs that should be linked to new_memory.
        """
        if not memory_store:
            return []

        # Stage 1: Cosine similarity retrieval
        candidates = self._retrieve_candidates(new_memory, memory_store, top_k)

        # Stage 2: LLM-confirmed links
        confirmed: list[str] = []
        for mem_id, mem in candidates:
            decision = self.llm_client.evaluate_link(
                new_content=new_memory.content,
                new_keywords=new_memory.keywords,
                candidate_content=mem.content,
                candidate_keywords=mem.keywords,
            )
            if decision.strip().upper() == "YES":
                confirmed.append(mem_id)

        return confirmed

    def _retrieve_candidates(
        self,
        new_memory: AgenticMemory,
        memory_store: List[AgenticMemory],
        top_k: int,
    ) -> List[tuple[str, AgenticMemory]]:
        """Retrieve top-k most similar memories by cosine similarity.

        Args:
            new_memory: The query memory.
            memory_store: All existing memories.
            top_k: Number of candidates to return.

        Returns:
            List of (memory_id, memory) tuples sorted by descending similarity.
        """
        # Build embedding matrix — exclude self if present
        ids: list[str] = []
        mats: list[np.ndarray] = []
        for mem in memory_store:
            if mem.id == new_memory.id:
                continue
            ids.append(mem.id)
            mats.append(mem.embedding)

        if not mats:
            return []

        matrix = np.stack(mats)  # (N, D)
        query = new_memory.embedding  # (D,)

        # Cosine similarity (embeddings are already normalized)
        sims = matrix @ query  # (N,)
        top_indices = np.argsort(sims)[::-1][:top_k]

        results: list[tuple[str, AgenticMemory]] = []
        for idx in top_indices:
            mem = memory_store[
                next(i for i, m in enumerate(memory_store) if m.id == ids[idx])
            ]
            results.append((ids[idx], mem))

        return results
