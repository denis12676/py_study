"""Centralized logging configuration for CLI and dashboard entrypoints."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


class TokenRedactionFilter(logging.Filter):
    """Best-effort token redaction in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = record.msg.replace("Authorization", "Authorization(redacted)")
        return True


def setup_logging(level: str | int | None = None) -> None:
    """Configure root logger only once."""
    root = logging.getLogger()
    if root.handlers:
        return

    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    token_filter = TokenRedactionFilter()
    stream_handler.addFilter(token_filter)
    file_handler.addFilter(token_filter)

    root.setLevel(log_level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
