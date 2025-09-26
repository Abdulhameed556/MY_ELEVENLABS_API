"""
Request Models for TTS API
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict
from enum import Enum
import re


class AudioFormat(str, Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"


class VoiceType(str, Enum):
    """Supported voice identifiers"""
    ADAM = "adam"
    SARAH = "sarah"
    ARNOLD = "arnold"


class VoiceSettings(BaseModel):
    """Custom voice configuration"""
    stability: Optional[float] = Field(
        0.7, ge=0.0, le=1.0, description="Voice stability"
    )
    similarity_boost: Optional[float] = Field(
        0.6, ge=0.0, le=1.0, description="Similarity boost"
    )
    style: Optional[float] = Field(
        0.2, ge=0.0, le=1.0, description="Speaking style"
    )
    use_speaker_boost: Optional[bool] = Field(
        True, description="Enable speaker boost"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stability": 0.7,
                "similarity_boost": 0.6,
                "style": 0.2,
                "use_speaker_boost": True,
            }
        }
    )


class TTSGenerateRequest(BaseModel):
    """Request model for TTS generation"""

    news_id: str = Field(
        ..., description="Unique identifier for the news article"
    )
    title: str = Field(
        ..., min_length=1, max_length=200, description="Article title"
    )
    body: str = Field(
        ..., min_length=10, max_length=10000, description="Article content"
    )
    voice: VoiceType = Field(VoiceType.ADAM, description="Voice identifier")
    format: AudioFormat = Field(
        AudioFormat.MP3, description="Audio output format"
    )
    sample_rate: Optional[int] = Field(
        22050, ge=8000, le=48000, description="Audio sample rate"
    )
    
    # Optional metadata
    metadata: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    
    # Optional voice config
    voice_settings: Optional[VoiceSettings] = None

    @field_validator("title", "body")
    @classmethod
    def validate_text_content(cls, v: str):
        """Validate text content is not empty after stripping"""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v.strip()

    @field_validator("news_id")
    @classmethod
    def validate_news_id(cls, v: str):
        """Validate news_id format"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "news_id must be alphanumeric with optional '_' or '-'"
            )
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "news_id": "news_12345",
                "title": "Global Push for Renewable Energy Gains Momentum",
                "body": (
                    "In recent years, the global energy landscape has been "
                    "undergoing a dramatic transformation..."
                ),
                "voice": "sarah",
                "format": "mp3",
                "sample_rate": 22050,
                "metadata": {
                    "author": "John Doe",
                    "category": "environment",
                    "source": "news_cms",
                },
                "voice_settings": {
                    "stability": 0.7,
                    "similarity_boost": 0.6,
                    "style": 0.2,
                    "use_speaker_boost": True,
                },
            }
        }
    )


class VoiceConfigRequest(BaseModel):
    """Request model for updating/retrieving voice configuration.

    Currently a placeholder to allow typed input; updates not implemented yet.
    """

    voice_settings: Optional[VoiceSettings] = None
    description: Optional[str] = None
    category: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.65,
                    "style": 0.25,
                    "use_speaker_boost": True,
                },
                "description": "Updated description",
                "category": "news",
            }
        }
    )
