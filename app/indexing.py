"""Indexing pipeline: text -> chunks -> embeddings -> FAISS.

This module ties the embedder and the vector store together. It owns the
chunking strategy (fixed-size character windows with overlap) which is the
single biggest lever on retrieval quality for a simple RAG system.
"""

from __future__ import annotations

import logging
import uuid

from .embeddings import EmbeddingService
from .vector_store import ChunkRecord, VectorStore

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping fixed-size character windows.

    Overlap preserves context that would otherwise be cut mid-sentence at a
    chunk boundary, improving retrieval recall.

    Args:
        text: The full document text.
        chunk_size: Maximum characters per chunk (must be > 0).
        overlap: Characters shared between consecutive chunks. Clamped to be
            strictly smaller than ``chunk_size`` to guarantee forward progress.

    Returns:
        A list of non-empty chunk strings (empty if ``text`` is blank).
    """
    text = text.strip()
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    # Guard: overlap >= chunk_size would loop forever, so clamp it.
    overlap = max(0, min(overlap, chunk_size - 1))

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap  # how far the window advances each iteration
    while start < len(text):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


class IndexingPipeline:
    """Orchestrates chunking, embedding, and storage of a document."""

    def __init__(
        self,
        embedder: EmbeddingService,
        store: VectorStore,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """Wire the pipeline to its collaborators and chunking parameters.

        Args:
            embedder: Service that turns text into vectors.
            store: Destination FAISS-backed vector store.
            chunk_size: Characters per chunk.
            chunk_overlap: Overlap characters between chunks.
        """
        self.embedder = embedder
        self.store = store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def index_document(self, text: str, source: str) -> dict:
        """Chunk, embed, and store one document's text.

        Args:
            text: Extracted plain text of the document.
            source: Original filename, kept for citation in answers.

        Returns:
            A summary dict with ``doc_id``, ``source`` and ``chunks`` count.

        Raises:
            ValueError: If ``text`` contains no indexable content.
        """
        chunks = chunk_text(text, self.chunk_size, self.chunk_overlap)
        if not chunks:
            raise ValueError("document produced no indexable text")

        doc_id = uuid.uuid4().hex[:12]
        vectors = self.embedder.embed_batch(chunks)
        records = [
            ChunkRecord(
                id=f"{doc_id}:{i}",
                doc_id=doc_id,
                source=source,
                text=chunk,
            )
            for i, chunk in enumerate(chunks)
        ]
        self.store.add(vectors, records)
        logger.info("Indexed document %s (%s) -> %d chunks", doc_id, source, len(chunks))
        return {"doc_id": doc_id, "source": source, "chunks": len(chunks)}
