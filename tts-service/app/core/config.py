"""
Configuration Management for TTS Service
"""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from enum import Enum


class LogLevel(str, Enum):
    """Standard logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application Settings with environment variable support"""

    # App Settings
    app_name: str = "TTS Microservice"
    debug: bool = False

    # ElevenLabs Configuration
    elevenlabs_api_key: str
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Request Settings
    max_text_length: int = 10000
    default_chunk_size: int = 2500
    request_timeout: int = 30

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    log_level: LogLevel = LogLevel.INFO

    # Security
    allowed_origins: List[str] = ["*"]  # Set explicitly in production

    @field_validator("elevenlabs_api_key")
    def validate_api_key(cls, v: str) -> str:
        if not v or v == "YOUR_API_KEY_HERE":
            raise ValueError("ElevenLabs API key is required")
        return v

    # Pydantic v2 settings config - resolve .env from project root
    _project_root = Path(__file__).resolve().parents[2]
    model_config = SettingsConfigDict(
        env_file=str(_project_root / ".env"),
        env_prefix="TTS_",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def load_voice_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load voice configuration from YAML file"""
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
            voices = config.get("voices", {})

            # Basic validation
            for name, details in voices.items():
                if "voice_id" not in details or "model" not in details:
                    raise ValueError(f"Invalid voice config for {name}")

            return voices

    except FileNotFoundError:
        logging.warning(
            "config.yaml not found. Using default voice configuration."
        )
        return {
            "adam": {
                "voice_id": "pNInz6obpgDQGcFmaJgB",
                "model": "eleven_flash_v2_5",
                "description": "Authoritative Male",
                "category": "news",
            },
            "sarah": {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "model": "eleven_turbo_v2_5",
                "description": "Professional Female",
                "category": "news",
            },
            "arnold": {
                "voice_id": "VR6AewLTigWG4xSOukaG",
                "model": "eleven_multilingual_v2",
                "description": "Engaging Male",
                "category": "premium",
            },
        }
    except Exception as e:
        raise RuntimeError(f"Error loading voice config: {e}")


# Initialize settings once
settings = get_settings()
