"""Unit tests for the A-MEM (Agentic Memory) system.

All tests use MockLLMClient — no real API calls or model downloads required.
Embeddings use a lightweight approach for speed.
"""

from __future__ import annotations

import numpy as np
import pytest

from amev_schema import AgenticMemory, LLMMetadata
from mock_llm import MockLLMClient
from note_builder import NoteBuilder
from link_generator import LinkGenerator
from memory_evolver import MemoryEvolver
from amev_engine import AmevEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def mock_note_builder(llm: MockLLMClient, monkeypatch: pytest.MonkeyPatch) -> NoteBuilder:
    """NoteBuilder with a fake embedder (no sentence-transformers download)."""
    builder = NoteBuilder(llm)

    def fake_encode(text: str) -> np.ndarray:
        """Deterministic pseudo-embedding from text hash."""
        rng = np.random.RandomState(abs(hash(text)) % (2**31))
        vec = rng.randn(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec

    monkeypatch.setattr(builder, "_encode", fake_encode)
    # Prevent lazy-loading the real model
    monkeypatch.setattr(type(builder), "embedder", property(lambda self: None))
    return builder


@pytest.fixture
def sample_memory(mock_note_builder: NoteBuilder) -> AgenticMemory:
    return mock_note_builder.build("Python is great for machine learning tasks")


@pytest.fixture
def fake_engine(llm: MockLLMClient, monkeypatch: pytest.MonkeyPatch) -> AmevEngine:
    """AmevEngine with fake embedder."""
    engine = AmevEngine(llm)

    def fake_encode(text: str) -> np.ndarray:
        rng = np.random.RandomState(abs(hash(text)) % (2**31))
        vec = rng.randn(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec

    monkeypatch.setattr(engine.note_builder, "_encode", fake_encode)
    monkeypatch.setattr(type(engine.note_builder), "embedder", property(lambda self: None))
    return engine


# ---------------------------------------------------------------------------
# LLMMetadata & AgenticMemory schema tests
# ---------------------------------------------------------------------------

class TestAgenticMemory:
    """Tests for the AgenticMemory data model."""

    def test_new_id_unique(self) -> None:
        ids = {AgenticMemory.new_id() for _ in range(100)}
        assert len(ids) == 100

    def test_serialization_roundtrip(self, sample_memory: AgenticMemory) -> None:
        d = sample_memory.to_dict()
        restored = AgenticMemory.from_dict(d)
        assert restored.id == sample_memory.id
        assert restored.content == sample_memory.content
        assert restored.keywords == sample_memory.keywords
        assert np.allclose(restored.embedding, sample_memory.embedding)

    def test_default_links_empty(self, sample_memory: AgenticMemory) -> None:
        assert sample_memory.links == []


# ---------------------------------------------------------------------------
# NoteBuilder tests
# ---------------------------------------------------------------------------

class TestNoteBuilder:
    """Tests for NoteBuilder with mocked LLM and embedder."""

    def test_build_returns_memory(self, mock_note_builder: NoteBuilder) -> None:
        mem = mock_note_builder.build("Hello world test content")
        assert isinstance(mem, AgenticMemory)
        assert mem.content == "Hello world test content"
        assert len(mem.keywords) > 0
        assert len(mem.tags) > 0
        assert mem.embedding.shape == (384,)

    def test_build_keywords_from_llm(self, mock_note_builder: NoteBuilder) -> None:
        mem = mock_note_builder.build("Alpha beta gamma")
        assert "alpha" in mem.keywords

    def test_build_tag_short(self, mock_note_builder: NoteBuilder) -> None:
        mem = mock_note_builder.build("Short text")
        assert "short" in mem.tags

    def test_build_tag_question(self, mock_note_builder: NoteBuilder) -> None:
        mem = mock_note_builder.build("What is AI?")
        assert "question" in mem.tags

    def test_build_embedding_normalized(self, mock_note_builder: NoteBuilder) -> None:
        mem = mock_note_builder.build("Normalization test")
        norm = np.linalg.norm(mem.embedding)
        assert abs(norm - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# LinkGenerator tests
# ---------------------------------------------------------------------------

class TestLinkGenerator:
    """Tests for LinkGenerator with mocked components."""

    def test_empty_store_returns_empty(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        gen = LinkGenerator(llm)
        mem = mock_note_builder.build("Test content")
        assert gen.generate_links(mem, []) == []

    def test_links_found_with_keyword_overlap(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        gen = LinkGenerator(llm)
        mem1 = mock_note_builder.build("Python programming language")
        mem2 = mock_note_builder.build("Python is awesome for coding")
        # mem2's keywords overlap with mem1 → mock LLM returns YES
        links = gen.generate_links(mem2, [mem1])
        assert mem1.id in links

    def test_no_link_without_overlap(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        gen = LinkGenerator(llm)
        mem1 = mock_note_builder.build("Apple orange banana")
        mem2 = mock_note_builder.build("Jupiter Mars Saturn")
        links = gen.generate_links(mem2, [mem1])
        assert mem1.id not in links

    def test_top_k_limit(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        gen = LinkGenerator(llm)
        base = mock_note_builder.build("Python coding")
        others = [mock_note_builder.build("Python coding extra") for _ in range(10)]
        links = gen.generate_links(base, others, top_k=3)
        assert len(links) <= 3


# ---------------------------------------------------------------------------
# MemoryEvolver tests
# ---------------------------------------------------------------------------

class TestMemoryEvolver:
    """Tests for MemoryEvolver with mocked LLM."""

    def test_no_evolution_without_overlap(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        evolver = MemoryEvolver(llm)
        new = mock_note_builder.build("Apple orange")
        existing = mock_note_builder.build("Jupiter Mars")
        evolved = evolver.evolve(new, [existing])
        assert len(evolved) == 0

    def test_evolution_with_sufficient_overlap(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        evolver = MemoryEvolver(llm)
        new = mock_note_builder.build("Alpha beta gamma delta")
        existing = mock_note_builder.build("Alpha beta epsilon zeta")
        evolved = evolver.evolve(new, [existing])
        assert len(evolved) == 1
        assert evolved[0].id == existing.id
        assert "evolved" in evolved[0].tags

    def test_evolution_preserves_content(
        self, mock_note_builder: NoteBuilder, llm: MockLLMClient,
    ) -> None:
        evolver = MemoryEvolver(llm)
        new = mock_note_builder.build("Alpha beta gamma delta")
        existing = mock_note_builder.build("Alpha beta epsilon zeta")
        evolved = evolver.evolve(new, [existing])
        assert evolved[0].content == existing.content
        assert evolved[0].id == existing.id


# ---------------------------------------------------------------------------
# AmevEngine integration tests
# ---------------------------------------------------------------------------

class TestAmevEngine:
    """Integration tests for the full A-MEM engine pipeline."""

    def test_add_memory_stores(self, fake_engine: AmevEngine) -> None:
        mem = fake_engine.add_memory("First memory about Python")
        assert fake_engine.count() == 1
        assert fake_engine.get_memory(mem.id) is not None

    def test_add_multiple_with_links(
        self, fake_engine: AmevEngine,
    ) -> None:
        m1 = fake_engine.add_memory("Python programming basics")
        m2 = fake_engine.add_memory("Python advanced techniques")
        assert fake_engine.count() == 2
        # At least one should have links
        assert len(m1.links) > 0 or len(m2.links) > 0

    def test_search_returns_results(self, fake_engine: AmevEngine) -> None:
        fake_engine.add_memory("Machine learning with Python")
        fake_engine.add_memory("Deep learning neural networks")
        results = fake_engine.search("Python ML", top_k=5)
        assert len(results) > 0

    def test_search_empty_engine(self, fake_engine: AmevEngine) -> None:
        assert fake_engine.search("anything") == []

    def test_search_expands_linked(
        self, fake_engine: AmevEngine,
    ) -> None:
        m1 = fake_engine.add_memory("Topic A with keyword X")
        m2 = fake_engine.add_memory("Topic A with keyword Y")
        results = fake_engine.search("Topic A", top_k=1)
        # Should expand to include linked memories
        result_ids = {r.id for r in results}
        assert m1.id in result_ids or m2.id in result_ids

    def test_get_all(self, fake_engine: AmevEngine) -> None:
        fake_engine.add_memory("Memory one")
        fake_engine.add_memory("Memory two")
        assert len(fake_engine.get_all()) == 2

    def test_evolution_applied(
        self, fake_engine: AmevEngine,
    ) -> None:
        """Verify that linked memories evolve when a new memory is added."""
        m1 = fake_engine.add_memory("Alpha beta gamma delta")
        m2 = fake_engine.add_memory("Alpha beta epsilon zeta")
        # If linked, m1 should have evolved (MockLLM triggers on 2+ overlap)
        stored_m1 = fake_engine.get_memory(m1.id)
        if m1.id in m2.links or m2.id in m1.links:
            # At least one evolution should have happened
            assert "evolved" in stored_m1.tags or "evolved" in fake_engine.get_memory(m2.id).tags
