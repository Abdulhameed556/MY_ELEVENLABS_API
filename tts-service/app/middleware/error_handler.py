#!/usr/bin/env python3
"""
error_handler.py
Global exception handling middleware for the TTS API
- Handles custom and generic exceptions
- Returns structured error responses
- Logs context-rich error information
"""

import traceback
import logging
from datetime import datetime, UTC
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from app.models.response_models import TTSErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

# ----------------------------
# Custom Exception Base
# ----------------------------


class TTSException(Exception):
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        retryable: bool = False,
    ):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(message)


class ElevenLabsException(TTSException):
    """Exception for upstream ElevenLabs-related errors.

    Accepts optional HTTP status code to map to an ErrorCode automatically.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        # Map common upstream status codes to our domain error codes
        if status_code == 401:
            error_code = ErrorCode.AUTH_ERROR
        elif status_code == 403:
            error_code = ErrorCode.FORBIDDEN
        elif status_code == 429:
            error_code = ErrorCode.UPSTREAM_RATE_LIMIT
        elif status_code in {500, 502, 503, 504}:
            error_code = ErrorCode.UPSTREAM_ERROR
        else:
            # Default for other cases when status code is unknown
            error_code = ErrorCode.UPSTREAM_ERROR

        super().__init__(
            message=message,
            error_code=error_code,
            retryable=retryable,
        )


class ValidationException(TTSException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT,
            retryable=False,
        )


class VoiceNotFoundException(TTSException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code=ErrorCode.VOICE_NOT_FOUND,
            retryable=False,
        )


# ----------------------------
# Error Code → HTTP Status Map
# ----------------------------

ERROR_STATUS_MAP = {
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.VOICE_NOT_FOUND: 404,
    ErrorCode.AUTH_ERROR: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.UPSTREAM_RATE_LIMIT: 429,
    ErrorCode.UPSTREAM_ERROR: 503,
    ErrorCode.TIMEOUT: 503,
    ErrorCode.INTERNAL_ERROR: 500,
}


# ----------------------------
# Helper: Build Error Response
# ----------------------------

def build_error_response(
    request_id: str,
    error_code: ErrorCode,
    message: str,
    retryable: bool = False,
    status_code: int = None
) -> JSONResponse:
    """Builds and returns a structured JSON error response"""

    response = TTSErrorResponse(
        request_id=request_id,
        error_code=error_code,
        message=message,
        retryable=retryable,
        timestamp=datetime.now(UTC).isoformat()
    )

    http_status = status_code or ERROR_STATUS_MAP.get(error_code, 500)

    # Use Pydantic's JSON mode to ensure datetimes and enums are serializable
    return JSONResponse(status_code=http_status, content=response.model_dump(mode="json"))


# ----------------------------
# Global Exception Handler
# ----------------------------

async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch and transform exceptions into structured error responses"""

    request_id = getattr(request.state, "request_id", "unknown")

    # 1. Custom TTS Exceptions
    if isinstance(exc, TTSException):
        logger.error(
            "[TTSException] request_id=%s, error_code=%s, "
            "retryable=%s, message=%s, traceback=%s",
            request_id,
            exc.error_code,
            exc.retryable,
            exc.message,
            traceback.format_exc(),
        )
        return build_error_response(
            request_id=request_id,
            error_code=exc.error_code,
            message=exc.message,
            retryable=exc.retryable
        )

    # 2. FastAPI HTTP Exceptions
    if isinstance(exc, HTTPException):
        error_code = (
            ErrorCode.INVALID_INPUT if exc.status_code < 500
            else ErrorCode.INTERNAL_ERROR
        )
        logger.warning(
            "[HTTPException] request_id=%s, status=%s, detail=%s, "
            "traceback=%s",
            request_id,
            exc.status_code,
            exc.detail,
            traceback.format_exc(),
        )
        return build_error_response(
            request_id=request_id,
            error_code=error_code,
            message=str(exc.detail),
            status_code=exc.status_code
        )

    # 3. Unexpected Exceptions
    logger.critical(
        "[UnhandledException] request_id=%s, type=%s, error=%s, traceback=%s",
        request_id,
        type(exc).__name__,
        str(exc),
        traceback.format_exc(),
    )
    return build_error_response(
        request_id=request_id,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        retryable=False
    )


# ----------------------------
# Middleware Adapter
# ----------------------------

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """ASGI middleware routing exceptions to our global handler.

    Keeps app.main import stable (app.add_middleware(ErrorHandlerMiddleware)).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ):
        try:
            return await call_next(request)  # noqa: BLE001
        except (TTSException, HTTPException) as exc:
            # Delegate to the shared exception handler for consistent responses
            return await exception_handler(request, exc)
        except Exception as exc:  # noqa: BLE001
            # Ensure any unexpected error is handled consistently
            return await exception_handler(request, exc)
