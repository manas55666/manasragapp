"""Shared pytest fixtures.

Every test runs in OFFLINE mode against a throwaway temp directory, so the
suite needs no Gemini key and never touches the network or real data dirs.
"""

from __future__ import annotations

import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Return offline Settings rooted at a per-test temporary directory.

    Args:
        tmp_path: pytest's built-in unique temp directory fixture.

    Returns:
        A :class:`Settings` instance with small, deterministic parameters.
    """
    return Settings(
        offline_mode=True,
        embedding_dim=64,
        data_dir=str(tmp_path / "data"),
        upload_dir=str(tmp_path / "uploads"),
        log_file=str(tmp_path / "logs" / "app.log"),
        chunk_size=200,
        chunk_overlap=40,
        top_k=3,
    )
