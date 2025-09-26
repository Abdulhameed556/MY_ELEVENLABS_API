"""
Structured Logging Configuration
"""

import logging
import sys
import json
import uuid
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from contextlib import contextmanager
from app.core.config import settings  # ✅ use settings for log_level


class StructuredFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""

        # Base log structure
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        extra_fields = [
            "request_id", "news_id", "voice_id", "duration_ms",
            "chars_count", "error_code", "user_agent",
            "trace_id", "span_id"
        ]
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """Configure structured logging for the application"""

    logger = logging.getLogger("tts_service")
    logger.setLevel(getattr(logging, (log_level or settings.log_level).upper()))

    # Remove existing handlers (avoid duplication in reloads)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance"""
    return logging.getLogger("tts_service")


class ContextAdapter(logging.LoggerAdapter):
    """LoggerAdapter for structured context logging"""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


@contextmanager
def log_request_context(
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    **kwargs
):
    """Context manager to add request-specific logging context"""

    if request_id is None:
        request_id = str(uuid.uuid4())

    logger = get_logger()
    context_data = {"request_id": request_id, "trace_id": trace_id, "span_id": span_id, **kwargs}
    context_logger = ContextAdapter(logger, context_data)

    try:
        yield context_logger
    except Exception as e:
        context_logger.error(
            f"Request failed: {str(e)}",
            exc_info=True,
            extra={"error_code": "REQUEST_FAILED"},
        )
        raise


# Initialize logger once
logger = setup_logging()