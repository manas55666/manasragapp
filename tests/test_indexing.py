"""Tests for the chunking helper and indexing pipeline."""

from __future__ import annotations

from app.embeddings import EmbeddingService
from app.indexing import IndexingPipeline, chunk_text
from app.vector_store import VectorStore


def test_chunk_text_splits_with_overlap():
    """Chunks should cover the text and advance by (size - overlap)."""
    text = "abcdefghij" * 30  # 300 chars
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 3
    assert all(len(c) <= 100 for c in chunks)


def test_chunk_text_empty_returns_empty():
    """Blank input should produce no chunks."""
    assert chunk_text("   ", chunk_size=100, overlap=10) == []


def test_chunk_text_overlap_clamped(monkeypatch):
    """Overlap >= size must be clamped so chunking still terminates."""
    chunks = chunk_text("x" * 50, chunk_size=10, overlap=999)
    assert len(chunks) > 0


def test_pipeline_indexes_chunks(settings):
    """Indexing a document should add one vector per produced chunk."""
    embedder = EmbeddingService(settings)
    store = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)
    pipeline = IndexingPipeline(
        embedder, store, settings.chunk_size, settings.chunk_overlap
    )

    result = pipeline.index_document("hello world. " * 100, source="demo.txt")

    assert result["chunks"] > 0
    assert store.size == result["chunks"]
    assert result["source"] == "demo.txt"
