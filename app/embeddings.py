"""Embedding generation via Google Gemini.

A thin wrapper around the Gemini embeddings API with one important fallback:
when ``offline_mode`` is enabled (or no API key is configured) we generate a
*deterministic local embedding* from a hash of the text. That keeps the whole
app — and its test-suite — runnable with zero credentials and no network,
while production uses the real ``text-embedding-004`` model.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np

from .config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Produce L2-normalised embedding vectors for text.

    Vectors are normalised so that an inner-product FAISS index behaves as a
    cosine-similarity index (cosine == dot product for unit vectors).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the service and configure the Gemini client if possible.

        Args:
            settings: Application settings carrying the API key, model id,
                embedding dimensionality, and the offline flag.
        """
        self.settings = settings
        # We run in offline mode when explicitly asked OR when no key is set.
        self._offline = settings.offline_mode or not settings.gemini_api_key

        if not self._offline:
            # Imported lazily so the dependency/key is only needed for real use.
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            self._genai = genai
            logger.info("EmbeddingService using Gemini model %s", settings.embedding_model)
        else:
            logger.warning("EmbeddingService running in OFFLINE mode (hash embeddings)")

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Create a deterministic pseudo-embedding from text (offline fallback).

        The same text always maps to the same vector, so retrieval still works
        sensibly for tests and local demos without calling an external API.

        Args:
            text: Input text to embed.

        Returns:
            A float32 vector of length ``settings.embedding_dim``.
        """
        dim = self.settings.embedding_dim
        # Seed a RNG with a stable hash of the text -> reproducible vector.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        return rng.standard_normal(dim).astype("float32")

    @staticmethod
    def _normalise(vec: np.ndarray) -> np.ndarray:
        """Scale a vector to unit length (guarding against divide-by-zero).

        Args:
            vec: The raw embedding vector.

        Returns:
            The L2-normalised vector as float32.
        """
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec.astype("float32")
        return (vec / norm).astype("float32")

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single string.

        Args:
            text: The text to embed.

        Returns:
            A unit-length float32 embedding vector.
        """
        if self._offline:
            return self._normalise(self._hash_embedding(text))

        # Real Gemini call; ``embed_content`` returns {"embedding": [...]}.
        result = self._genai.embed_content(
            model=self.settings.embedding_model, content=text
        )
        vec = np.asarray(result["embedding"], dtype="float32")
        return self._normalise(vec)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed many strings, returning a matrix with one row per input.

        Args:
            texts: List of texts to embed.

        Returns:
            A 2-D float32 array of shape ``(len(texts), embedding_dim)``. An
            empty input yields an empty, correctly-shaped array.
        """
        if not texts:
            return np.empty((0, self.settings.embedding_dim), dtype="float32")
        # Embed row-by-row to keep the code simple and provider-agnostic.
        return np.vstack([self.embed_text(t) for t in texts])
