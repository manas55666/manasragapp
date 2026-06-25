# Spec Kit — Technical Plan: RAG Service

## Architecture
```
Client ──HTTP──> FastAPI (app/main.py)
                  ├── upload.py     extract text (pdf/txt/docx)
                  ├── indexing.py   chunk -> embed -> store
                  ├── embeddings.py Gemini text-embedding-004 (offline fallback)
                  ├── vector_store.py FAISS IndexFlatIP + JSON metadata (persisted)
                  └── rag.py        retrieve top-k -> Gemini gemini-2.0-flash
```

## Key Decisions
- **FAISS `IndexFlatIP`** with unit-normalised vectors == cosine similarity;
  exact search is fine at free-tier corpus sizes and needs no training.
- **Gemini API** for embeddings/generation keeps RAM low (no local model).
- **Offline mode** (hash embeddings + extractive answer) makes the app and CI
  run with no key or network.
- **Persistence**: `index.faiss` + `records.json` written on every add; loaded
  on startup. Backups are a tar of `data/` synced to S3.

## Components & Files
| Concern | File |
|---|---|
| Settings | `app/config.py` |
| Logging | `app/logging_config.py` |
| Embeddings | `app/embeddings.py` |
| Vector store | `app/vector_store.py` |
| Indexing pipeline | `app/indexing.py` |
| Upload/parse | `app/upload.py` |
| RAG | `app/rag.py` |
| API | `app/main.py` |

## Testing
- Unit: chunking, vector store search/persistence.
- Integration: FastAPI TestClient upload→query, validation errors.
- All offline; coverage exported to `coverage.xml` for SonarCloud.
