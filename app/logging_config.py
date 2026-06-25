"""Structured logging configuration.

Logs are emitted as one JSON object per line to both stdout (captured by
Docker / the platform) and a size-rotated file (so the EC2 disk never fills).
JSON lines are trivial to ship to CloudWatch or grep locally.
"""

from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler


class JsonFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single-line JSON string."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialise one log record to JSON.

        Args:
            record: The log record produced by the logging framework.

        Returns:
            A JSON string with timestamp, level, logger name, and message,
            plus the exception traceback when present.
        """
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any structured context passed via ``logger.info(..., extra=...)``.
        if hasattr(record, "context"):
            payload["context"] = record.context  # type: ignore[attr-defined]
        # Include traceback text when the record carries exception info.
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log") -> None:
    """Configure root logging with JSON output to stdout and a rotating file.

    Safe to call more than once: existing handlers are cleared first so we do
    not emit duplicate lines when the app reloads.

    Args:
        log_level: Minimum level to emit (e.g. ``"INFO"``).
        log_file: Destination path for the rotating file handler. Parent
            directories are created if missing.
    """
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.handlers.clear()  # avoid duplicate handlers on re-init / hot reload

    formatter = JsonFormatter()

    # Stream handler -> stdout, captured by Docker logging driver.
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    root.addHandler(stream)

    # Rotating file handler -> 5 files x 5 MB, bounding disk usage on EC2.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
