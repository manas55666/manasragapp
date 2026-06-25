"""File upload handling and text extraction.

Supports ``.txt``, ``.pdf`` and ``.docx``. Each helper turns raw bytes into
plain text so the indexing pipeline can stay format-agnostic.
"""

from __future__ import annotations

import io
import logging
import os
import uuid

logger = logging.getLogger(__name__)

# File extensions we know how to extract text from.
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def save_upload(content: bytes, filename: str, upload_dir: str) -> str:
    """Persist uploaded bytes to disk under a collision-free name.

    A short UUID prefix prevents two uploads with the same name from
    overwriting each other.

    Args:
        content: Raw file bytes.
        filename: Original client-provided filename.
        upload_dir: Directory to write into (created if missing).

    Returns:
        The absolute path the file was written to.
    """
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{os.path.basename(filename)}"
    path = os.path.join(upload_dir, safe_name)
    with open(path, "wb") as fh:
        fh.write(content)
    logger.info("Saved upload %s (%d bytes)", path, len(content))
    return path


def extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from uploaded bytes based on the file extension.

    Args:
        content: Raw file bytes.
        filename: Original filename, used only to detect the extension.

    Returns:
        The extracted UTF-8 text (whitespace-stripped).

    Raises:
        ValueError: If the extension is not supported.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext or '(none)'}")

    if ext == ".txt":
        return content.decode("utf-8", errors="ignore").strip()
    if ext == ".pdf":
        return _extract_pdf(content)
    return _extract_docx(content)


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF bytes, concatenating all pages.

    Args:
        content: Raw PDF bytes.

    Returns:
        The combined page text.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX bytes, joining non-empty paragraphs.

    Args:
        content: Raw DOCX bytes.

    Returns:
        The combined paragraph text.
    """
    import docx  # python-docx

    document = docx.Document(io.BytesIO(content))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()
