"""
Request Logging Middleware
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logger import get_logger
from app.middleware.error_handler import exception_handler


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses with correlation IDs"""

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        logger = get_logger()

        # Extract request info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        url = str(request.url)

        # Start timer
        start_time = time.perf_counter()

        # Log request start
        logger.info(
            f"Request started: {method} {url}",
            extra={
                "request_id": request_id,
                "method": method,
                "url": url,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "event_type": "request_start",
            },
        )

        try:
            # Process request
            response: Response = await call_next(request)

        except Exception as e:
            # Log unhandled exception and return structured JSON via global handler
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                f"Request failed: {method} {url} - {type(e).__name__}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "duration_ms": duration_ms,
                    "event_type": "request_error",
                },
            )
            error_response = await exception_handler(request, e)
            error_response.headers["X-Request-ID"] = request_id
            return error_response

        else:
            # Log success
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                f"Request completed: {method} {url} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "event_type": "request_complete",
                },
            )

            # Add request ID to response
            response.headers["X-Request-ID"] = request_id
            return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Get client IP from headers or connection info"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"