# MANAS RAG App (Task 1)

A containerized **Retrieval-Augmented Generation** service built with FastAPI.
Upload documents, and ask questions answered strictly from their contents.

- **Embeddings & generation**: Google **Gemini** (`text-embedding-004`, `gemini-2.0-flash`)
- **Vector database**: **FAISS** (`IndexFlatIP`, persisted to disk)
- **Indexing pipeline**: extract → chunk (with overlap) → embed → store
- **File upload**: `.txt`, `.pdf`, `.docx`
- **Runs with zero credentials** via an offline (hash-embedding) fallback — ideal for tests/CI

> Part of the MANAS assessment. Task 2 (Node + React) lives in the separate
> `manas-fullstack-app` repository.

---

## Architecture

```
Client ──HTTP──> FastAPI (app/main.py)
                  ├── upload.py        extract text (pdf/txt/docx)
                  ├── indexing.py      chunk → embed → store
                  ├── embeddings.py    Gemini embeddings (offline fallback)
                  ├── vector_store.py  FAISS index + JSON metadata (persisted)
                  └── rag.py           retrieve top-k → Gemini answer
```

State lives in `data/` (`index.faiss` + `records.json`) and uploaded files in
`data/uploads/`. Logs are JSON lines in `logs/app.log` (and stdout).

---

## API

| Method | Path      | Body | Description |
|--------|-----------|------|-------------|
| GET    | `/health` | —    | Status, offline flag, indexed chunk count |
| POST   | `/upload` | multipart `file` | Upload + index a document |
| POST   | `/query`  | `{"question": "..."}` | Answer grounded in indexed docs |

`/query` returns `{"answer": "...", "sources": [{"id","source","score"}]}`.

---

## Quick start (Docker)

```bash
cp .env.example .env          # optionally add your GEMINI_API_KEY
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health

curl -F "file=@yourdoc.pdf" http://localhost:8000/upload

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What does the document say about X?"}'
```

> With **no** `GEMINI_API_KEY`, the app runs in **offline mode**: deterministic
> hash embeddings + extractive answers. Add a key (free from Google AI Studio)
> for real semantic search and generated answers.

---

## Local development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OFFLINE_MODE=true uvicorn app.main:app --reload
```

### Run tests & lint

```bash
OFFLINE_MODE=true pytest        # full suite runs offline, no key needed
ruff check app tests
```

---

## Configuration

All settings come from environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | _(empty)_ | Gemini key; empty ⇒ offline mode |
| `OFFLINE_MODE` | `false` | Force offline (no network) |
| `EMBEDDING_MODEL` | `models/text-embedding-004` | Embedding model |
| `GENERATION_MODEL` | `models/gemini-2.0-flash` | Generation model |
| `EMBEDDING_DIM` | `768` | Vector dimension (must match model) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Chunking |
| `TOP_K` | `4` | Chunks retrieved per query |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / `logs/app.log` | Logging |

---

## Code quality (SonarQube / SonarCloud)

`sonar-project.properties` configures the scan; CI runs `ruff`, exports
`coverage.xml` from pytest, and the SonarCloud GitHub Action publishes results.
Set the `SONAR_TOKEN` repository secret and your SonarCloud org/key.

## Spec Kit

Spec-driven artifacts live in `specs/` (`spec.md`, `plan.md`, `tasks.md`).

---

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push/PR to `main`:

1. **test** — ruff lint + pytest (offline) with coverage
2. **sonarcloud** — quality scan
3. **deploy** (main only) — build image → push to GHCR → SSH to EC2 →
   `docker compose pull && up -d`

Required secrets: `SONAR_TOKEN`, `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`
(`GITHUB_TOKEN` is built-in for GHCR).

---

## Logging & backup

- **Logging**: JSON lines to stdout (Docker-captured) and a rotating file
  (`logs/app.log`, 5×5 MB) via `app/logging_config.py`.
- **Backup**: `scripts/backup.sh` tars `data/` and `aws s3 sync`s it to a
  bucket. Schedule via cron, e.g. nightly:
  ```cron
  0 2 * * * /opt/manas-rag-app/scripts/backup.sh >> /var/log/rag-backup.log 2>&1
  ```

---

## Deployment (deferred)

Production runs on a single AWS free-tier EC2 instance behind Nginx +
Let's Encrypt (`deploy/nginx-rag.conf`). Full provisioning steps are tracked in
`specs/tasks.md` (T16–T19) and the root project `PLAN.md`.
