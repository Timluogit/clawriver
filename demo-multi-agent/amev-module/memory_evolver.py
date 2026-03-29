"""Memory Evolver: updates existing memories when new related memories arrive."""

from __future__ import annotations

from typing import List

from amev_schema import AgenticMemory, LLMClient


class MemoryEvolver:
    """Evolves existing memories based on newly added related memories.

    When a new memory is linked to existing ones, this component uses the LLM
    to analyze whether the existing memories should be updated — e.g., adding
    new keywords, refining context descriptions, or adjusting tags.

    The evolver does NOT mutate memories directly. It returns a list of updated
    copies, leaving the decision to apply changes to the caller (AmevEngine).

    Args:
        llm_client: LLM client implementing the LLMClient protocol.

    Example:
        >>> from mock_llm import MockLLMClient
        >>> evolver = MemoryEvolver(MockLLMClient())
        >>> updated = evolver.evolve(new_memory, linked_memories)
        >>> # updated contains evolved copies of linked_memories
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def evolve(
        self,
        new_memory: AgenticMemory,
        linked_memories: List[AgenticMemory],
    ) -> List[AgenticMemory]:
        """Analyze the impact of a new memory on its linked memories.

        For each linked memory, ask the LLM whether and how it should evolve.
        Returns a list of updated memory copies (only those that changed).

        Args:
            new_memory: The newly added memory triggering evolution.
            linked_memories: Memories linked to the new memory.

        Returns:
            List of evolved AgenticMemory copies. Memories that didn't need
            updates are NOT included in this list.
        """
        evolved: list[AgenticMemory] = []

        for existing in linked_memories:
            update = self.llm_client.analyze_evolution(
                new_content=new_memory.content,
                new_keywords=new_memory.keywords,
                existing_content=existing.content,
                existing_keywords=existing.keywords,
                existing_tags=existing.tags,
            )

            if update is not None:
                # Create an updated copy (immutable evolution)
                updated_memory = AgenticMemory(
                    id=existing.id,
                    content=existing.content,
                    timestamp=existing.timestamp,
                    keywords=update.keywords,
                    tags=update.tags,
                    context_desc=update.context_desc,
                    embedding=existing.embedding,
                    links=existing.links,
                )
                evolved.append(updated_memory)

        return evolved
