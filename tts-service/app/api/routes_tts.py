"""
TTS API Routes
"""

import io
import time
import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.models.request_models import TTSGenerateRequest, VoiceConfigRequest
from app.models.response_models import (
    TTSGenerateResponse,
    VoicesListResponse,
    HealthResponse,
    TTSStatus,
    VoiceInfo,
)
from app.services.elevenlabs_service import tts_service
 
from app.services.voice_manager import voice_manager
from app.core.logger import get_logger, log_request_context
# from app.core.config import settings
from app.utils.audio_utils import get_audio_info, validate_audio_data
from app.middleware.error_handler import ValidationException, TTSException
from app.middleware.metrics import metrics


router = APIRouter(prefix="/tts", tags=["TTS"])
logger = get_logger()


@router.post("/generate")
async def generate_tts(request: TTSGenerateRequest, http_request: Request):
    """
    Generate TTS audio from text content.
    
    Returns JSON metadata + audio stream.
    The Node.js backend should call this once per article and cache the result.
    """

    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))
    start_time = time.time()

    with log_request_context(
        request_id=request_id,
        news_id=request.news_id,
        voice=request.voice
    ) as context_logger:
        try:
            # Store voice in request state for metrics
            http_request.state.voice_used = request.voice

            # Validation
            if not voice_manager.is_voice_available(request.voice):
                raise ValidationException(
                    f"Voice '{request.voice}' is not available"
                )

            full_text = f"{request.title}. {request.body}"
            context_logger.info(
                (
                    f"TTS generation requested: {len(request.body)} chars, "
                    f"voice: {request.voice}"
                ),
                extra={
                    "chars_count": len(request.body),
                    "title_length": len(request.title),
                },
            )

            # Generate audio
            audio_data = await tts_service.text_to_speech(
                text=full_text,
                voice_name=request.voice,
                news_id=request.news_id,
                request_id=request_id
            )

            if not audio_data:
                raise TTSException(
                    "Failed to generate audio",
                    "GENERATION_FAILED",
                )
            if not validate_audio_data(audio_data):
                raise TTSException(
                    "Generated audio is invalid",
                    "INVALID_AUDIO",
                )

            audio_info = get_audio_info(audio_data)
            generation_time = int((time.time() - start_time) * 1000)

            # Metadata
            voice_config = voice_manager.get_voice_config(request.voice)
            metadata = TTSGenerateResponse(
                request_id=request_id,
                news_id=request.news_id,
                status=TTSStatus.SUCCESS,
                audio_size_bytes=len(audio_data),
                duration_seconds=audio_info.get("duration_seconds"),
                format=request.format.value,
                # If audio_info doesn't have frame_rate (e.g., pydub unavailable),
                # fall back to requested sample_rate to satisfy the response model
                sample_rate=(audio_info.get("frame_rate") or request.sample_rate),
                voice_used=request.voice,
                model_used=voice_config["model"],
                chars_processed=len(full_text),
                generation_time_ms=generation_time,
                created_at=datetime.now(UTC),
                metadata={
                    **request.metadata,
                    "audio_info": audio_info,
                    "voice_config": voice_config["description"]
                }
            )

            context_logger.info(
                (
                    f"TTS completed successfully: {len(audio_data)} bytes "
                    f"in {generation_time}ms"
                ),
                extra={
                    "audio_size_bytes": len(audio_data),
                    "duration_seconds": audio_info.get("duration_seconds"),
                },
            )

            # Return as multipart: JSON metadata + audio stream
            headers = {
                "X-Request-ID": request_id,
                "X-News-ID": request.news_id,
                "X-Voice-Used": request.voice,
                "X-Audio-Size": str(len(audio_data)),
                "X-Generation-Time": str(generation_time),
                "Content-Length": str(len(audio_data))
            }

            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type=f"audio/{request.format.value}",
                headers={"X-Metadata": metadata.model_dump_json(), **headers}
            )

        except (ValidationException, TTSException) as e:
            context_logger.error("TTS error: %s", e.message)
            metrics.record_error(
                e.error_code.value,
                request.voice,
                e.retryable,
            )
            raise
        except Exception as e:  # noqa: BLE001
            context_logger.error("Unexpected error: %s", str(e), exc_info=True)
            metrics.record_error(
                "INTERNAL_ERROR",
                getattr(request, "voice", "unknown"),
                True,
            )
            raise TTSException(
                f"Internal error: {str(e)}",
                "INTERNAL_ERROR",
                retryable=True,
            ) from e


@router.get("/voices", response_model=VoicesListResponse)
async def list_voices(request: Request):
    """Return all available voices for TTS generation."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        raw_voices = voice_manager.get_all_voices()

        # Normalize to VoiceInfo list to satisfy response_model even if mocks
        # return partial dicts
        voices: list[VoiceInfo] = []
        for v in raw_voices:
            if isinstance(v, VoiceInfo):
                voices.append(v)
            elif isinstance(v, dict):
                voices.append(
                    VoiceInfo(
                        voice_id=v.get("voice_id", "unknown"),
                        name=v.get("name", "unknown"),
                        description=v.get("description", ""),
                        model=v.get("model", "unknown"),
                        category=v.get("category", "custom"),
                        settings=v.get("settings", {}),
                    )
                )
            else:
                # Skip unknown entries defensively
                continue

        logger.info(
            "Voices list requested",
            extra={"request_id": request_id, "voice_count": len(voices)},
        )
        return VoicesListResponse(voices=voices, total_count=len(voices))
    except Exception as e:  # noqa: BLE001
        logger.error("Error getting voices list: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get voices list",
        ) from e


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check for monitoring and upstream (ElevenLabs) dependency."""
    try:
        upstream_status = {"elevenlabs": "unhealthy"}
        try:
            voices = await tts_service.get_voices()
            if voices:
                upstream_status["elevenlabs"] = "healthy"
        except TTSException:
            # Upstream error; keep as unhealthy
            pass

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(UTC),
            upstream_status=upstream_status
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Health check failed: %s", str(e))
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy",
        ) from e


@router.post("/voices/{voice_name}/config")
async def update_voice_config(
    voice_name: str,
    config_request: VoiceConfigRequest,
    request: Request,
):
    """Update or retrieve voice configuration (currently read-only)."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        if not voice_manager.is_voice_available(voice_name):
            raise HTTPException(
                status_code=404,
                detail=f"Voice '{voice_name}' not found",
            )
        voice_config = voice_manager.get_voice_config(voice_name)
        # mark argument as used (API is currently read-only)
        _ = config_request
        logger.info(
            "Voice config requested",
            extra={"request_id": request_id, "voice": voice_name},
        )
        return {
            "voice": voice_name,
            "current_config": voice_config,
            "message": (
                "Voice configuration retrieved (update not implemented yet)"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Error updating voice config: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update voice config",
        ) from e
