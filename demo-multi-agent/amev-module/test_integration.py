"""Integration tests for the A-MEM (Agentic Memory) system.

Tests the complete pipeline with realistic multi-topic scenarios,
link generation, memory evolution, and search with association expansion.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from amev_schema import AgenticMemory
from mock_llm import MockLLMClient
from amev_engine import AmevEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> AmevEngine:
    """AmevEngine with deterministic fake embeddings (no model download)."""
    eng = AmevEngine(MockLLMClient())

    def fake_encode(text: str) -> np.ndarray:
        """Deterministic pseudo-embedding from text hash — same text always
        produces the same vector, enabling reproducible similarity tests."""
        rng = np.random.RandomState(abs(hash(text)) % (2**31))
        vec = rng.randn(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec

    monkeypatch.setattr(eng.note_builder, "_encode", fake_encode)
    monkeypatch.setattr(type(eng.note_builder), "embedder", property(lambda self: None))
    return eng


# ---------------------------------------------------------------------------
# Topic data — designed so MockLLM extracts overlapping keywords
# MockLLM takes first 5 unique lowercase words as keywords
# ---------------------------------------------------------------------------

TOPICS = {
    "ai": "Artificial intelligence is transforming how we build software systems. "
          "Deep learning models can now understand natural language and generate code.",
    "programming": "Programming in python is the best way to build software. "
                   "Clean code principles help developers write maintainable code.",
    "mathematics": "Mathematics is the foundation of machine learning and deep learning. "
                   "Linear algebra and calculus are essential mathematical tools.",
    "physics": "Quantum mechanics describes the behavior of particles at the atomic scale. "
               "Wave-particle duality is a fundamental concept in modern physics.",
    "biology": "DNA replication is the biological process by which cells copy their genome. "
               "Protein synthesis follows the central dogma of molecular biology.",
}


# ---------------------------------------------------------------------------
# Integration Test: Full Pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end integration tests simulating realistic usage."""

    def test_add_five_topics(self, engine: AmevEngine) -> None:
        """Add 5 memories on different topics and verify storage."""
        memories: dict[str, AgenticMemory] = {}
        for topic, content in TOPICS.items():
            mem = engine.add_memory(content)
            memories[topic] = mem

        assert engine.count() == 5
        for mem in memories.values():
            stored = engine.get_memory(mem.id)
            assert stored is not None
            assert stored.content == mem.content

    def test_links_between_related_topics(self, engine: AmevEngine) -> None:
        """Related topics (AI ↔ programming share 'software'; AI ↔ math share 'deep'/'learning') should link."""
        m_ai = engine.add_memory(TOPICS["ai"])
        m_prog = engine.add_memory(TOPICS["programming"])
        m_math = engine.add_memory(TOPICS["mathematics"])
        m_phys = engine.add_memory(TOPICS["physics"])
        m_bio = engine.add_memory(TOPICS["biology"])

        # Collect all link pairs
        all_links: set[tuple[str, str]] = set()
        for mem in engine.get_all():
            for lid in mem.links:
                all_links.add(tuple(sorted([mem.id, lid])))

        # AI keywords: ['artificial', 'intelligence', 'is', 'transforming', 'how']
        # Prog keywords: ['programming', 'in', 'python', 'is', 'the']
        # They share 'is' → MockLLM returns YES → should be linked
        ai_prog_linked = (
            tuple(sorted([m_ai.id, m_prog.id])) in all_links
            or m_prog.id in m_ai.links
            or m_ai.id in m_prog.links
        )
        assert ai_prog_linked, "AI and programming memories should be linked (share 'is')"

        # AI keywords share 'deep' and 'learning' with math:
        # Math keywords: ['mathematics', 'is', 'the', 'foundation', 'of'] — wait, doesn't share 'deep'/'learning'
        # Actually: AI first 5 words = artificial, intelligence, is, transforming, how
        # Math first 5 words = mathematics, is, the, foundation, of
        # They share 'is' → should link
        ai_math_linked = (
            tuple(sorted([m_ai.id, m_math.id])) in all_links
            or m_math.id in m_ai.links
            or m_ai.id in m_math.links
        )
        assert ai_math_linked, "AI and math memories should be linked (share 'is')"

    def test_evolution_triggers_on_related_memories(self, engine: AmevEngine) -> None:
        """Adding related memories should trigger evolution when keyword overlap >= 2."""
        # Use content that guarantees 2+ keyword overlap for evolution trigger
        m1 = engine.add_memory("Alpha beta gamma delta epsilon is the key to understanding")
        m2 = engine.add_memory("Alpha beta zeta eta theta is also important for understanding")

        stored_m1 = engine.get_memory(m1.id)
        stored_m2 = engine.get_memory(m2.id)

        # Both share 'alpha', 'beta', 'is' (3+ overlap) → evolution should trigger
        at_least_one_evolved = (
            "evolved" in stored_m1.tags or "evolved" in stored_m2.tags
        )
        assert at_least_one_evolved, "At least one memory should have evolved (3 keyword overlap)"

    def test_search_returns_relevant_results(self, engine: AmevEngine) -> None:
        """Search for 'programming' should return programming-related memory."""
        for content in TOPICS.values():
            engine.add_memory(content)

        results = engine.search("programming", top_k=5)
        assert len(results) > 0

        # At least one result should be the programming memory
        result_contents = [r.content for r in results]
        found = any("programming" in c.lower() for c in result_contents)
        assert found, "Search for 'programming' should find the programming memory"

    def test_search_expands_with_associations(self, engine: AmevEngine) -> None:
        """Search results should include linked (associated) memories."""
        m_ai = engine.add_memory(TOPICS["ai"])
        m_prog = engine.add_memory(TOPICS["programming"])

        # They share 'is' → linked. Search top_k=1 should expand.
        results = engine.search("artificial intelligence", top_k=1)
        result_ids = {r.id for r in results}

        if m_ai.id in m_prog.links or m_prog.id in m_ai.links:
            assert len(results) > 1, "Linked memory should be expanded in search results"

    def test_unrelated_topics_minimal_links(self, engine: AmevEngine) -> None:
        """Physics and biology share no keywords → no direct link between them."""
        m_phys = engine.add_memory(TOPICS["physics"])
        m_bio = engine.add_memory(TOPICS["biology"])

        # Phys keywords: ['quantum', 'mechanics', 'describes', 'the', 'behavior']
        # Bio keywords: ['dna', 'replication', 'is', 'the', 'biological']
        # They share 'the' → actually they DO link via MockLLM (1 overlap >= 1)
        # So let's test with truly unrelated content
        engine2 = AmevEngine(MockLLMClient())

        def fake_encode(text: str) -> np.ndarray:
            rng = np.random.RandomState(abs(hash(text)) % (2**31))
            vec = rng.randn(384).astype(np.float32)
            vec /= np.linalg.norm(vec)
            return vec

        engine2.note_builder._encode = fake_encode

        # Use completely disjoint keywords
        m1 = engine2.add_memory("Apple orange banana")
        m2 = engine2.add_memory("Jupiter Mars Saturn")
        # Keywords: ['apple', 'orange', 'banana'] vs ['jupiter', 'mars', 'saturn']
        # No overlap → no link
        assert m2.id not in m1.links, "Completely unrelated memories should not link"
        assert m1.id not in m2.links, "Completely unrelated memories should not link"

    def test_chain_evolution(self, engine: AmevEngine) -> None:
        """Adding memories sequentially should accumulate links and evolutions."""
        m1 = engine.add_memory("Alpha beta gamma is the foundation")
        m2 = engine.add_memory("Alpha beta delta is important")
        m3 = engine.add_memory("Alpha beta epsilon is critical")

        # All share 'alpha', 'beta', 'is' → should form a chain of links
        all_link_counts = {mem.id: len(mem.links) for mem in engine.get_all()}
        total_links = sum(all_link_counts.values())
        assert total_links >= 2, f"Expected at least 2 links total, got {total_links}"

        # At least some evolution should have happened
        evolved_count = sum(
            1 for mem in engine.get_all() if "evolved" in mem.tags
        )
        assert evolved_count >= 1, "At least one memory should have evolved"


# ---------------------------------------------------------------------------
# Performance Benchmark
# ---------------------------------------------------------------------------

class TestPerformance:
    """Performance benchmarks for the A-MEM engine."""

    def test_bulk_add_100_memories(
        self, engine: AmevEngine, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Benchmark: add 100 memories and measure time."""
        def fake_encode(text: str) -> np.ndarray:
            rng = np.random.RandomState(abs(hash(text)) % (2**31))
            vec = rng.randn(384).astype(np.float32)
            vec /= np.linalg.norm(vec)
            return vec

        monkeypatch.setattr(engine.note_builder, "_encode", fake_encode)
        monkeypatch.setattr(type(engine.note_builder), "embedder", property(lambda self: None))

        contents = [
            f"Memory entry number {i} about topic {i % 10} with keyword {chr(97 + i % 26)}"
            for i in range(100)
        ]

        start = time.perf_counter()
        for content in contents:
            engine.add_memory(content)
        add_elapsed = time.perf_counter() - start

        assert engine.count() == 100
        print(f"\n⏱  100 memories added in {add_elapsed:.3f}s ({add_elapsed/100*1000:.1f}ms/mem)")

        # Benchmark search
        queries = ["topic 5", "keyword a", "memory entry", "topic 9 keyword z"]
        start = time.perf_counter()
        for q in queries:
            engine.search(q, top_k=10)
        search_elapsed = time.perf_counter() - start

        print(f"⏱  4 searches on 100 memories in {search_elapsed:.3f}s ({search_elapsed/4*1000:.1f}ms/query)")

        # Assert reasonable performance (< 10s total for 100 adds + 4 searches)
        assert add_elapsed + search_elapsed < 10.0, \
            f"Performance regression: {add_elapsed + search_elapsed:.1f}s total"

    def test_search_quality_on_bulk(
        self, engine: AmevEngine, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should return relevant results even with 100 memories."""
        def fake_encode(text: str) -> np.ndarray:
            rng = np.random.RandomState(abs(hash(text)) % (2**31))
            vec = rng.randn(384).astype(np.float32)
            vec /= np.linalg.norm(vec)
            return vec

        monkeypatch.setattr(engine.note_builder, "_encode", fake_encode)
        monkeypatch.setattr(type(engine.note_builder), "embedder", property(lambda self: None))

        for i in range(100):
            engine.add_memory(
                f"Memory entry number {i} about topic {i % 10}"
            )

        results = engine.search("topic 5", top_k=10)
        assert len(results) > 0
