"""
Response Models for TTS API
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TTSStatus(str, Enum):
    """TTS Generation Status"""
    SUCCESS = "success"
    FAILED = "failed"
    PROCESSING = "processing"


class ErrorCode(str, Enum):
    """Standardized error codes"""
    INVALID_INPUT = "INVALID_INPUT"
    AUTH_ERROR = "AUTH_ERROR"
    FORBIDDEN = "FORBIDDEN"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    UPSTREAM_RATE_LIMIT = "UPSTREAM_RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VOICE_NOT_FOUND = "VOICE_NOT_FOUND"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"


class VoiceInfo(BaseModel):
    """Voice information model"""
    
    voice_id: str = Field(..., description="ElevenLabs voice ID")
    name: str = Field(..., description="Human-readable voice name")
    description: str = Field(..., description="Voice description")
    model: str = Field(..., description="ElevenLabs model to use")
    category: str = Field(
        ..., description="Voice category (news, premium, etc.)"
    )
    settings: Dict[str, Any] = Field(..., description="Default voice settings")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "sarah",
                "description": "Professional Female",
                "model": "eleven_turbo_v2_5",
                "category": "news",
                "settings": {
                    "stability": 0.7,
                    "similarity_boost": 0.6,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            }
        }
    )


class TTSGenerateResponse(BaseModel):
    """Response model for successful TTS generation"""
    
    request_id: str = Field(..., description="Unique request identifier")
    news_id: str = Field(..., description="News article identifier")
    status: TTSStatus = Field(..., description="Generation status")
    
    # Audio information
    audio_size_bytes: int = Field(
        ..., description="Size of generated audio in bytes"
    )
    duration_seconds: Optional[float] = Field(
        None, description="Audio duration in seconds"
    )
    format: str = Field(..., description="Audio format")
    sample_rate: int = Field(..., description="Audio sample rate")
    
    # Generation metadata
    voice_used: str = Field(..., description="Voice identifier used")
    model_used: str = Field(..., description="ElevenLabs model used")
    chars_processed: int = Field(
        ..., description="Number of characters processed"
    )
    generation_time_ms: int = Field(
        ..., description="Time taken to generate audio"
    )
    
    # Timestamps
    created_at: datetime = Field(..., description="Generation timestamp")
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_abc123",
                "news_id": "news_12345",
                "status": "success",
                "audio_size_bytes": 1914716,
                "duration_seconds": 95.2,
                "format": "mp3",
                "sample_rate": 22050,
                "voice_used": "sarah",
                "model_used": "eleven_turbo_v2_5",
                "chars_processed": 1851,
                "generation_time_ms": 4210,
                "created_at": "2025-09-20T10:30:45Z",
                "metadata": {
                    "chunks_processed": 1,
                    "cost_estimate": 0.002
                }
            }
        }
    )


class TTSErrorResponse(BaseModel):
    """Error response model"""
    
    request_id: str = Field(..., description="Unique request identifier")
    error_code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[str] = Field(
        None, description="Additional error details"
    )
    retryable: bool = Field(
        False, description="Whether the request can be retried"
    )
    timestamp: datetime = Field(..., description="Error timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_xyz789",
                "error_code": "UPSTREAM_RATE_LIMIT",
                "message": "Rate limit exceeded for ElevenLabs API",
                "details": "Rate limit reset in 60 seconds",
                "retryable": True,
                "timestamp": "2025-09-20T10:30:45Z"
            }
        }
    )


class VoicesListResponse(BaseModel):
    """Response model for listing available voices"""
    
    voices: List[VoiceInfo] = Field(
        ..., description="List of available voices"
    )
    total_count: int = Field(..., description="Total number of voices")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "voices": [
                    {
                        "voice_id": "pNInz6obpgDQGcFmaJgB",
                        "name": "adam",
                        "description": "Authoritative Male",
                        "model": "eleven_flash_v2_5",
                        "category": "news",
                        "settings": {
                            "stability": 0.7,
                            "similarity_boost": 0.6
                        }
                    }
                ],
                "total_count": 3
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    upstream_status: Optional[Dict[str, str]] = Field(
        None, description="Upstream service status"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-09-20T10:30:45Z",
                "upstream_status": {
                    "elevenlabs": "healthy"
                }
            }
        }
    )
