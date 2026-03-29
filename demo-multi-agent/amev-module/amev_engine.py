"""A-MEM Engine: main orchestrator for the Agentic Memory system."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from amev_schema import AgenticMemory, LLMClient
from note_builder import NoteBuilder
from link_generator import LinkGenerator
from memory_evolver import MemoryEvolver


class AmevEngine:
    """Main engine for the A-MEM (Agentic Memory) self-evolving memory system.

    Orchestrates the full pipeline: build → link → evolve → store.
    Provides both structured memory insertion and context-aware retrieval.

    Args:
        llm_client: LLM client implementing the LLMClient protocol.
        model_name: Sentence-transformer model name (default: all-MiniLM-L6-v2).

    Example:
        >>> from mock_llm import MockLLMClient
        >>> engine = AmevEngine(MockLLMClient())
        >>> m = engine.add_memory("Python is great for AI development")
        >>> results = engine.search("programming languages", top_k=5)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.note_builder = NoteBuilder(llm_client, model_name)
        self.link_generator = LinkGenerator(llm_client)
        self.memory_evolver = MemoryEvolver(llm_client)
        self.memories: Dict[str, AgenticMemory] = {}

    def add_memory(self, content: str) -> AgenticMemory:
        """Add a new memory through the full A-MEM pipeline.

        Pipeline:
            1. **Build**: Extract metadata via LLM + generate embedding.
            2. **Link**: Find semantically related existing memories.
            3. **Evolve**: Update linked memories based on new context.
            4. **Store**: Persist the new memory and apply evolutions.

        Args:
            content: Raw interaction text to memorize.

        Returns:
            The newly created AgenticMemory (after linking and evolution).
        """
        # Step 1: Build
        memory = self.note_builder.build(content)

        # Step 2: Link
        existing = list(self.memories.values())
        linked_ids = self.link_generator.generate_links(memory, existing)
        memory.links = linked_ids

        # Step 3: Evolve linked memories
        linked_memories = [self.memories[mid] for mid in linked_ids if mid in self.memories]
        evolved = self.memory_evolver.evolve(memory, linked_memories)

        # Step 4: Store — apply evolutions
        for updated in evolved:
            self.memories[updated.id] = updated

        # Also add reverse links: linked memories should point back to new memory
        for mid in linked_ids:
            if mid in self.memories and memory.id not in self.memories[mid].links:
                self.memories[mid].links.append(memory.id)

        # Store the new memory
        self.memories[memory.id] = memory
        return memory

    def search(self, query: str, top_k: int = 10) -> List[AgenticMemory]:
        """Search memories with context-aware retrieval.

        Retrieval strategy:
            1. Encode query and compute cosine similarity against all memories.
            2. Return top-k results.
            3. Expand: for each result, also include its directly linked memories
               (if not already in the result set).

        Args:
            query: Search query text.
            top_k: Maximum number of primary results to return.

        Returns:
            List of AgenticMemory objects ranked by relevance.
        """
        if not self.memories:
            return []

        all_mems = list(self.memories.values())

        # Encode query
        query_vec = self.note_builder._encode(query)

        # Cosine similarity
        embeddings = np.stack([m.embedding for m in all_mems])
        sims = embeddings @ query_vec

        # Top-k primary results
        top_k = min(top_k, len(all_mems))
        top_indices = np.argsort(sims)[::-1][:top_k]
        primary = [all_mems[i] for i in top_indices]

        # Expand with linked memories
        seen_ids = {m.id for m in primary}
        expanded: list[AgenticMemory] = list(primary)
        for mem in primary:
            for linked_id in mem.links:
                if linked_id not in seen_ids and linked_id in self.memories:
                    expanded.append(self.memories[linked_id])
                    seen_ids.add(linked_id)

        return expanded

    def get_memory(self, memory_id: str) -> AgenticMemory | None:
        """Retrieve a specific memory by ID.

        Args:
            memory_id: The memory identifier.

        Returns:
            The AgenticMemory if found, None otherwise.
        """
        return self.memories.get(memory_id)

    def get_all(self) -> List[AgenticMemory]:
        """Return all stored memories.

        Returns:
            List of all AgenticMemory objects in the store.
        """
        return list(self.memories.values())

    def count(self) -> int:
        """Return the number of stored memories."""
        return len(self.memories)
