"""FastAPI application exposing the RAG service over HTTP.

Routes:
    GET  /health   -> liveness + index size
    POST /upload   -> upload a document, extract text, and index it
    POST /query    -> ask a question and get a grounded answer

Singletons (settings, embedder, vector store, pipelines) are created once at
import time and shared across requests, since FAISS and the Gemini client are
both cheap to keep resident and expensive to rebuild per request.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from .config import get_settings
from .embeddings import EmbeddingService
from .indexing import IndexingPipeline
from .logging_config import setup_logging
from .rag import RagService
from .upload import extract_text, save_upload
from .vector_store import VectorStore

# ---- Bootstrap shared singletons ------------------------------------------
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

embedder = EmbeddingService(settings)
vector_store = VectorStore(dim=settings.embedding_dim, data_dir=settings.data_dir)
pipeline = IndexingPipeline(
    embedder=embedder,
    store=vector_store,
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)
rag_service = RagService(settings, embedder, vector_store)

app = FastAPI(title="MANAS RAG App", version="1.0.0")


class QueryRequest(BaseModel):
    """Request body for the ``/query`` endpoint.

    Attributes:
        question: The natural-language question to answer.
    """

    question: str


@app.get("/health")
def health() -> dict:
    """Liveness probe used by Docker / the load balancer.

    Returns:
        A dict with service status, offline-mode flag, and current index size.
    """
    return {
        "status": "ok",
        "offline_mode": settings.offline_mode or not settings.gemini_api_key,
        "indexed_chunks": vector_store.size,
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Accept a document, persist it, extract text, and index it.

    Args:
        file: The multipart-uploaded file (``.txt`` / ``.pdf`` / ``.docx``).

    Returns:
        The indexing summary (``doc_id``, ``source``, ``chunks``).

    Raises:
        HTTPException: 400 for unsupported types or empty/blank documents.
    """
    content = await file.read()
    try:
        # Keep the raw file (for backups / re-indexing) then extract its text.
        save_upload(content, file.filename, settings.upload_dir)
        text = extract_text(content, file.filename)
        result = pipeline.index_document(text, source=file.filename)
    except ValueError as exc:
        logger.warning("Upload rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.post("/query")
def query(req: QueryRequest) -> dict:
    """Answer a question grounded in the indexed corpus.

    Args:
        req: Request body containing the ``question``.

    Returns:
        A dict with the generated ``answer`` and the ``sources`` used.

    Raises:
        HTTPException: 400 if the question is empty.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")
    return rag_service.answer(req.question)
