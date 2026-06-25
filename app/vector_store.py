"""FAISS-backed vector store with on-disk persistence.

We use ``IndexFlatIP`` (exact inner-product search). Because embeddings are
unit-normalised upstream, inner product == cosine similarity. The index plus a
parallel list of chunk metadata are persisted side-by-side so a restart (or a
restored backup) rehydrates the full searchable corpus.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass

import faiss
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ChunkRecord:
    """Metadata stored alongside each indexed vector.

    Attributes:
        id: Stable identifier (``"<doc_id>:<chunk_index>"``).
        doc_id: Identifier of the source document.
        source: Original filename the chunk came from.
        text: The chunk text, returned to the LLM as grounding context.
    """

    id: str
    doc_id: str
    source: str
    text: str


class VectorStore:
    """Thread-safe FAISS index plus aligned chunk metadata.

    Row ``i`` of the FAISS index corresponds to ``self._records[i]``.
    """

    def __init__(self, dim: int, data_dir: str) -> None:
        """Create or prepare a vector store rooted at ``data_dir``.

        Args:
            dim: Embedding dimensionality (must match the embedder).
            data_dir: Directory holding ``index.faiss`` and ``records.json``.
        """
        self.dim = dim
        self.data_dir = data_dir
        self._index_path = os.path.join(data_dir, "index.faiss")
        self._records_path = os.path.join(data_dir, "records.json")
        # A lock keeps concurrent FastAPI requests from corrupting the index.
        self._lock = threading.Lock()

        os.makedirs(data_dir, exist_ok=True)
        self._index = faiss.IndexFlatIP(dim)
        self._records: list[ChunkRecord] = []
        self.load()  # rehydrate any previously persisted state

    def add(self, vectors: np.ndarray, records: list[ChunkRecord]) -> None:
        """Add vectors and their metadata, then persist to disk.

        Args:
            vectors: Float32 array of shape ``(n, dim)``.
            records: ``n`` metadata records, aligned row-for-row with ``vectors``.

        Raises:
            ValueError: If the row counts or dimensionality do not match.
        """
        if len(vectors) != len(records):
            raise ValueError("vectors and records length mismatch")
        if vectors.size and vectors.shape[1] != self.dim:
            raise ValueError(f"expected dim {self.dim}, got {vectors.shape[1]}")
        if not records:
            return

        with self._lock:
            self._index.add(vectors.astype("float32"))
            self._records.extend(records)
            self._persist()
        logger.info("Indexed %d chunks (total=%d)", len(records), len(self._records))

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[ChunkRecord, float]]:
        """Return the ``top_k`` most similar chunks to a query vector.

        Args:
            query_vector: A single embedding of shape ``(dim,)`` or ``(1, dim)``.
            top_k: Maximum number of results to return.

        Returns:
            A list of ``(ChunkRecord, score)`` pairs ordered by descending
            similarity. Empty if the index has no vectors yet.
        """
        if self._index.ntotal == 0:
            return []

        # FAISS expects a 2-D query matrix.
        q = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        scores, indices = self._index.search(q, min(top_k, self._index.ntotal))

        results: list[tuple[ChunkRecord, float]] = []
        for idx, score in zip(indices[0], scores[0], strict=False):
            if idx == -1:  # FAISS uses -1 to pad when fewer than top_k exist
                continue
            results.append((self._records[idx], float(score)))
        return results

    def _persist(self) -> None:
        """Write the FAISS index and records JSON to disk (caller holds lock)."""
        faiss.write_index(self._index, self._index_path)
        with open(self._records_path, "w", encoding="utf-8") as fh:
            json.dump([asdict(r) for r in self._records], fh, ensure_ascii=False)

    def load(self) -> None:
        """Load a previously persisted index + records if both files exist.

        Missing or mismatched files are tolerated: the store simply starts
        empty, which is the correct behaviour on a fresh deployment.
        """
        if os.path.exists(self._index_path) and os.path.exists(self._records_path):
            self._index = faiss.read_index(self._index_path)
            with open(self._records_path, encoding="utf-8") as fh:
                self._records = [ChunkRecord(**r) for r in json.load(fh)]
            logger.info("Loaded vector store with %d chunks", len(self._records))

    @property
    def size(self) -> int:
        """Number of vectors currently held in the index."""
        return self._index.ntotal
