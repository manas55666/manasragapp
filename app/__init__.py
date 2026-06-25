"""manas-rag-app — Retrieval-Augmented Generation service.

This package contains a small, self-contained RAG application:

- ``config``          : environment-driven settings
- ``logging_config``  : structured JSON logging setup
- ``embeddings``      : Google Gemini embedding wrapper
- ``vector_store``    : FAISS index (add / search / persist / load)
- ``indexing``        : chunking + indexing pipeline
- ``upload``          : file saving + text extraction (pdf/txt/docx)
- ``rag``             : retrieval + Gemini answer generation
- ``main``            : FastAPI app exposing the REST API
"""

__version__ = "1.0.0"
