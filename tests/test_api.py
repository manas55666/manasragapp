"""End-to-end API tests using FastAPI's TestClient.

Environment variables force offline mode and a temp data dir BEFORE importing
``app.main`` (whose singletons read settings at import time).
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a TestClient backed by a fresh, offline app instance.

    Args:
        tmp_path: Temp directory for the index/uploads/logs.
        monkeypatch: Used to set env vars before importing the app module.

    Returns:
        A configured :class:`fastapi.testclient.TestClient`.
    """
    monkeypatch.setenv("OFFLINE_MODE", "true")
    monkeypatch.setenv("EMBEDDING_DIM", "64")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "logs" / "app.log"))

    # get_settings() is cached; clear it so our env vars take effect.
    from app import config

    config.get_settings.cache_clear()

    import app.main as main

    importlib.reload(main)  # rebuild singletons against the temp settings
    return TestClient(main.app)


def test_health_ok(client):
    """/health returns status ok and a zero index on a fresh app."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["indexed_chunks"] == 0


def test_upload_then_query(client):
    """Uploading a .txt then querying it returns a grounded answer + sources."""
    files = {"file": ("note.txt", b"The capital of France is Paris.", "text/plain")}
    up = client.post("/upload", files=files)
    assert up.status_code == 200
    assert up.json()["chunks"] >= 1

    q = client.post("/query", json={"question": "What is the capital of France?"})
    assert q.status_code == 200
    body = q.json()
    assert "Paris" in body["answer"]
    assert len(body["sources"]) >= 1


def test_upload_unsupported_type_rejected(client):
    """An unsupported extension yields a 400 error."""
    files = {"file": ("bad.xyz", b"data", "application/octet-stream")}
    resp = client.post("/upload", files=files)
    assert resp.status_code == 400


def test_empty_question_rejected(client):
    """A blank question yields a 400 error."""
    resp = client.post("/query", json={"question": "   "})
    assert resp.status_code == 400
