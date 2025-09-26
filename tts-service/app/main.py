"""
FastAPI TTS Microservice Main Application
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

from app.core.config import settings
from app.core.logger import setup_logging, get_logger
from app.api.routes_tts import router as tts_router
from app.middleware.request_logger import RequestLoggingMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.metrics import MetricsMiddleware, create_metrics_endpoint
from app.services.elevenlabs_service import tts_service


# Initialize logging
setup_logging(settings.log_level)
logger = get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup & shutdown lifecycle handler"""
    logger.info(
        "Starting %s",
        settings.app_name,
        extra={"version": "1.0.0", "debug": settings.debug},
    )
    yield
    logger.info(
        "Shutting down %s",
        settings.app_name,
        extra={"event": "shutdown"},
    )
    # Ensure HTTP client is cleanly closed
    if hasattr(tts_service, "client") and not tts_service.client.is_closed:
        try:
            await tts_service.aclose()
        except (httpx.HTTPError, RuntimeError):
            # Avoid raising during shutdown; log at debug level if needed
            logger.debug(
                "AsyncClient already closed or failed to close cleanly"
            )


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Production-ready Text-to-Speech microservice using ElevenLabs API"
        ),
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "tts", "description": "Text-to-Speech operations"},
            {"name": "health", "description": "Service health & monitoring"},
        ]
    )

    # Add middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    application.add_middleware(ErrorHandlerMiddleware)
    application.add_middleware(MetricsMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    # Routes
    application.include_router(tts_router, prefix="/v1")

    if settings.enable_metrics:
        application.add_api_route(
            "/metrics",
            create_metrics_endpoint(),
            methods=["GET"],
        )

    @application.get("/", tags=["health"])
    async def root():
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "status": "healthy",
            "docs_url": "/docs" if settings.debug else None,
            "endpoints": {
                "tts_generate": "/v1/tts/generate",
                "list_voices": "/v1/tts/voices",
                "health_check": "/v1/tts/health",
                "metrics": "/metrics" if settings.enable_metrics else None,
            }
        }

    return application


# FastAPI app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=False,
    )
