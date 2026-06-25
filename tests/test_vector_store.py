"""Tests for the FAISS vector store: search, persistence, and reload."""

from __future__ import annotations

from app.embeddings import EmbeddingService
from app.vector_store import ChunkRecord, VectorStore


def _records(texts):
    """Build ChunkRecord list from raw texts for test convenience."""
    return [
        ChunkRecord(id=f"d:{i}", doc_id="d", source="t.txt", text=t)
        for i, t in enumerate(texts)
    ]


def test_search_returns_most_similar(settings):
    """A query equal to an indexed chunk should rank that chunk first."""
    embedder = EmbeddingService(settings)
    store = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)

    texts = ["the cat sat on the mat", "quantum physics is hard", "I love pizza"]
    store.add(embedder.embed_batch(texts), _records(texts))

    hits = store.search(embedder.embed_text("quantum physics is hard"), top_k=1)
    assert hits[0][0].text == "quantum physics is hard"


def test_persistence_round_trip(settings):
    """A new store pointed at the same dir should reload prior vectors."""
    embedder = EmbeddingService(settings)
    store = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)
    texts = ["alpha", "beta"]
    store.add(embedder.embed_batch(texts), _records(texts))

    reopened = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)
    assert reopened.size == 2


def test_search_empty_index_returns_empty(settings):
    """Searching before anything is indexed returns no hits, no errors."""
    embedder = EmbeddingService(settings)
    store = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)
    assert store.search(embedder.embed_text("anything"), top_k=3) == []
