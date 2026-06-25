# Spec Kit — Specification: RAG Service

> Spec-driven development artifact (GitHub Spec Kit format). Describes WHAT and
> WHY; see `plan.md` for HOW and `tasks.md` for the work breakdown.

## Goal
Provide an HTTP service that lets a user upload documents and ask questions
answered strictly from those documents (Retrieval-Augmented Generation).

## User Stories
- **US-1**: As a user, I can upload a `.txt`/`.pdf`/`.docx` file and have it
  indexed, so its contents become searchable.
- **US-2**: As a user, I can ask a natural-language question and receive an
  answer grounded in my uploaded documents, with source citations.
- **US-3**: As an operator, I can check service health and rely on logs +
  nightly backups for observability and recovery.

## Functional Requirements
1. `POST /upload` accepts a single file, extracts text, chunks it, embeds the
   chunks, and stores them in a vector index.
2. `POST /query` embeds the question, retrieves top-k chunks, and generates an
   answer constrained to the retrieved context.
3. `GET /health` reports status, offline mode, and index size.
4. Unsupported file types and empty inputs return HTTP 400.

## Non-Functional Requirements
- Runs within AWS free-tier (1 GB RAM): no in-RAM ML model; embeddings via the
  Gemini API; FAISS index is the only stateful component.
- Zero-credential local/test execution via deterministic offline embeddings.
- Structured JSON logs; index + uploads persisted and backed up to S3.

## Out of Scope
- Multi-user auth, document deletion/versioning, and streaming responses.

## Acceptance Criteria
- Upload→query round-trip returns the expected fact with at least one source.
- Test suite passes with no API key (offline mode).
