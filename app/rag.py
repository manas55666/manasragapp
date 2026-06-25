"""Retrieval-Augmented Generation: retrieve context, then generate an answer.

The query is embedded, the most similar chunks are pulled from the vector
store, and those chunks are stuffed into a prompt that instructs Gemini to
answer *only* from the provided context. In offline mode (no API key) we skip
the LLM and return an extractive answer built from the retrieved chunks, so the
endpoint always responds.
"""

from __future__ import annotations

import logging

from .config import Settings
from .embeddings import EmbeddingService
from .vector_store import ChunkRecord, VectorStore

logger = logging.getLogger(__name__)

# Prompt template instructing the model to stay grounded in the context.
PROMPT_TEMPLATE = """You are a helpful assistant. Answer the question using ONLY the context below.
If the answer is not contained in the context, say you don't know.

Context:
{context}

Question: {question}

Answer:"""


class RagService:
    """Answer questions grounded in the indexed corpus."""

    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingService,
        store: VectorStore,
    ) -> None:
        """Initialise retrieval + (optional) Gemini generation.

        Args:
            settings: Application settings (model id, top_k, offline flag).
            embedder: Shared embedding service (reused for query embedding).
            store: Vector store to retrieve grounding chunks from.
        """
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self._offline = settings.offline_mode or not settings.gemini_api_key

        if not self._offline:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel(settings.generation_model)

    def _build_context(self, records: list[ChunkRecord]) -> str:
        """Join retrieved chunks into a single, source-labelled context block.

        Args:
            records: Retrieved chunk records, most relevant first.

        Returns:
            A newline-separated string with each chunk prefixed by its source.
        """
        return "\n\n".join(f"[{r.source}] {r.text}" for r in records)

    def answer(self, question: str) -> dict:
        """Retrieve context for a question and generate a grounded answer.

        Args:
            question: The user's natural-language question.

        Returns:
            A dict with the ``answer`` string and the list of ``sources``
            (chunk id, source filename, similarity score) used to produce it.
        """
        query_vec = self.embedder.embed_text(question)
        hits = self.store.search(query_vec, self.settings.top_k)

        if not hits:
            return {"answer": "No documents have been indexed yet.", "sources": []}

        records = [r for r, _ in hits]
        context = self._build_context(records)

        if self._offline:
            # Extractive fallback: surface the single best-matching chunk.
            answer = records[0].text
        else:
            prompt = PROMPT_TEMPLATE.format(context=context, question=question)
            response = self._model.generate_content(prompt)
            answer = (response.text or "").strip()

        sources = [
            {"id": r.id, "source": r.source, "score": round(score, 4)}
            for r, score in hits
        ]
        logger.info("Answered question using %d sources", len(sources))
        return {"answer": answer, "sources": sources}
