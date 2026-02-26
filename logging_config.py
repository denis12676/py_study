"""Centralized logging configuration for CLI and dashboard entrypoints."""

from __future__ import annotations

import contextvars
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Tuple


_CORRELATION_ID = contextvars.ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _CORRELATION_ID.get()


def set_correlation_id(correlation_id: str):
    return _CORRELATION_ID.set(correlation_id)


def reset_correlation_id(token) -> None:
    _CORRELATION_ID.reset(token)


def ensure_correlation_id(prefix: str = "req") -> Tuple[object | None, str]:
    current = get_correlation_id()
    if current and current != "-":
        return None, current
    value = f"{prefix}-{uuid.uuid4().hex[:12]}"
    token = set_correlation_id(value)
    return token, value


class TokenRedactionFilter(logging.Filter):
    """Best-effort token redaction in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = record.msg.replace("Authorization", "Authorization(redacted)")
        return True


class CorrelationIdFilter(logging.Filter):
    """Inject correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str | int | None = None) -> None:
    """Configure root logger only once."""
    root = logging.getLogger()
    if root.handlers:
        return

    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = os.getenv("LOG_FORMAT", "plain").lower()

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | [cid=%(correlation_id)s] %(message)s",
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
    cid_filter = CorrelationIdFilter()
    for handler in (stream_handler, file_handler):
        handler.addFilter(token_filter)
        handler.addFilter(cid_filter)

    root.setLevel(log_level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
