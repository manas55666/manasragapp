# Spec Kit — Task Breakdown: RAG Service

## Application
- [x] T1 Settings loader (`config.py`)
- [x] T2 Structured JSON logging (`logging_config.py`)
- [x] T3 Gemini embedding wrapper + offline fallback (`embeddings.py`)
- [x] T4 FAISS vector store with persistence (`vector_store.py`)
- [x] T5 Chunking + indexing pipeline (`indexing.py`)
- [x] T6 Upload + text extraction for txt/pdf/docx (`upload.py`)
- [x] T7 Retrieval + Gemini generation (`rag.py`)
- [x] T8 FastAPI routes /health /upload /query (`main.py`)

## Quality & Tests
- [x] T9 Unit + integration tests (offline)
- [x] T10 Ruff lint config (`pyproject.toml`)
- [x] T11 SonarCloud config (`sonar-project.properties`)

## Packaging & Ops
- [x] T12 Dockerfile + docker-compose
- [x] T13 CI/CD workflow (test → sonar → build → deploy)
- [x] T14 Backup script (`scripts/backup.sh`)
- [x] T15 Nginx reverse-proxy vhost (`deploy/nginx-rag.conf`)

## Deployment (deferred — needs AWS account/domain/keys)
- [ ] T16 Provision EC2 + Elastic IP + security group + swap
- [ ] T17 Install Docker, point DNS, run Certbot for HTTPS
- [ ] T18 Configure GitHub secrets + first deploy
- [ ] T19 S3 backup bucket + cron entry
