"""
Structured logging system for the Structured Output Agent.

Provides configurable logging with JSON formatting, file persistence,
request/response traceability, and separate log levels.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# ─── Log Formatting ───────────────────────────────────────────────────────────

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
JSON_LOG_FORMAT = "%(message)s"


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    Includes all standard fields plus extras from the LogRecord.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(
                    traceback.format_exception(*record.exc_info)
                ),
            }

        # Add extra fields from the 'extra' dict
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Add the 'extra' kwarg fields
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "message", "module", "msecs", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName", "extra_fields",
            ):
                if not key.startswith("_"):
                    try:
                        json.dumps({key: value})
                        log_entry[key] = value
                    except (TypeError, ValueError):
                        log_entry[key] = str(value)

        return json.dumps(log_entry, default=str)


class ReadableFormatter(logging.Formatter):
    """Human-readable log formatter with color support."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.utcfromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        message = record.getMessage()

        # Truncate long messages for readability
        if len(message) > 2000:
            message = message[:2000] + "..."

        formatted = (
            f"{timestamp} | {level_color}{record.levelname:8s}{self.RESET} | "
            f"{record.name:<20s} | {message}"
        )

        if record.exc_info and record.exc_info[0]:
            formatted += "\n" + "".join(
                traceback.format_exception(*record.exc_info)
            )

        return formatted


# ─── Logger Factory ───────────────────────────────────────────────────────────

_loggers: Dict[str, logging.Logger] = {}
_configured = False


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_structured: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
) -> None:
    """
    Configure the root logger with handlers and formatters.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, console only.
        enable_structured: If True, use JSON format in file handler.
        max_file_size_mb: Maximum size of each log file in MB.
        backup_count: Number of rotated log files to keep.
    """
    global _configured

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (readable format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.setFormatter(ReadableFormatter())
    root_logger.addHandler(console_handler)

    # File handler (JSON structured format)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))

        if enable_structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(ReadableFormatter())

        root_logger.addHandler(file_handler)

    # Disable noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Ensures the logger is configured and applies structured logging
    enhancements.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured Logger instance.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    # Store original method
    original_info = logger.info
    original_warning = logger.warning
    original_error = logger.error
    original_debug = logger.debug
    original_critical = logger.critical

    class EnhancedLogger:
        """Wrapper that adds structured extra fields support."""

        def __init__(self, logger_obj: logging.Logger):
            self._logger = logger_obj

        def debug(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
            if extra:
                self._logger.debug(msg, *args, extra={"extra_fields": extra, **extra}, **kwargs)
            else:
                self._logger.debug(msg, *args, **kwargs)

        def info(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
            if extra:
                self._logger.info(msg, *args, extra={"extra_fields": extra, **extra}, **kwargs)
            else:
                self._logger.info(msg, *args, **kwargs)

        def warning(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
            if extra:
                self._logger.warning(msg, *args, extra={"extra_fields": extra, **extra}, **kwargs)
            else:
                self._logger.warning(msg, *args, **kwargs)

        def error(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
            if extra:
                self._logger.error(msg, *args, extra={"extra_fields": extra, **extra}, **kwargs)
            else:
                self._logger.error(msg, *args, **kwargs)

        def critical(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
            if extra:
                self._logger.critical(msg, *args, extra={"extra_fields": extra, **extra}, **kwargs)
            else:
                self._logger.critical(msg, *args, **kwargs)

        def __getattr__(self, attr):
            return getattr(self._logger, attr)

    enhanced = EnhancedLogger(logger)
    _loggers[name] = enhanced  # type: ignore
    return enhanced  # type: ignore


# ─── Log Query / Analytics ────────────────────────────────────────────────────

def read_logs(
    log_file: str = "logs/agent.log",
    level: Optional[str] = None,
    limit: int = 100,
    request_id: Optional[str] = None,
) -> list[Dict[str, Any]]:
    """
    Read and filter log entries from the structured log file.

    Args:
        log_file: Path to the log file.
        level: Filter by log level (e.g., "ERROR").
        limit: Maximum number of entries to return.
        request_id: Filter by request ID.

    Returns:
        List of parsed log entries.
    """
    entries = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    entry = {"raw": line}

                if level and entry.get("level") != level.upper():
                    continue
                if request_id and entry.get("request_id") != request_id:
                    continue

                entries.append(entry)
                if len(entries) >= limit:
                    break
    except FileNotFoundError:
        pass

    return entries


def get_validation_stats(log_file: str = "logs/agent.log") -> Dict[str, Any]:
    """
    Aggregate validation statistics from log files.

    Returns:
        Dict with counts of successes, failures, retries, etc.
    """
    stats: Dict[str, Any] = {
        "total_entries": 0,
        "info_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "validation_success": 0,
        "validation_failure": 0,
        "retry_attempts": 0,
        "unique_request_ids": set(),
    }

    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                stats["total_entries"] += 1
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                level = entry.get("level", "")
                if level == "INFO":
                    stats["info_count"] += 1
                elif level == "WARNING":
                    stats["warning_count"] += 1
                elif level == "ERROR":
                    stats["error_count"] += 1

                msg = entry.get("message", "")
                if "Validation successful" in msg:
                    stats["validation_success"] += 1
                elif "Validation failed" in msg:
                    stats["validation_failure"] += 1
                elif "Retry attempt" in msg:
                    stats["retry_attempts"] += 1

                if "request_id" in entry:
                    stats["unique_request_ids"].add(entry["request_id"])
    except FileNotFoundError:
        pass

    stats["unique_request_ids"] = len(stats["unique_request_ids"])
    return stats
