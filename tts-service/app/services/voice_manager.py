"""
Voice Manager for Dynamic Voice Switching
"""

from typing import Dict, List, Any
from threading import Lock
from pydantic import BaseModel, Field, ValidationError
from app.core.config import load_voice_config
from app.models.response_models import VoiceInfo
from app.middleware.error_handler import VoiceNotFoundException
from app.core.logger import get_logger


class VoiceSchema(BaseModel):
    """Schema for validating voice configurations."""
    voice_id: str
    model: str
    description: str
    category: str = "custom"
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "stability": 0.7,
        "similarity_boost": 0.6,
        "style": 0.2,
        "use_speaker_boost": True
    })


class VoiceManager:
    """Manages voice configurations and switching."""

    def __init__(self, config_path: str = "config.yaml"):
        self.logger = get_logger()
        self._lock = Lock()
        self._voices: Dict[str, Dict[str, Any]] = load_voice_config(
            config_path
        )
        self.logger.info(
            "Loaded %d voices from configuration", len(self._voices)
        )

    def get_voice_config(self, voice_name: str) -> Dict[str, Any]:
        """Get configuration for a specific voice."""
        if voice_name not in self._voices:
            raise VoiceNotFoundException(voice_name)
        return self._voices[voice_name].copy()

    def get_all_voices(self) -> List[VoiceInfo]:
        """Get all available voices as VoiceInfo objects."""
        return [
            VoiceInfo(
                voice_id=config["voice_id"],
                name=name,
                description=config["description"],
                model=config["model"],
                category=config.get("category", "custom"),
                settings=config.get("settings", {})
            )
            for name, config in self._voices.items()
        ]

    def is_voice_available(self, voice_name: str) -> bool:
        """Check if a voice is available."""
        return voice_name in self._voices

    def get_voice_settings(self, voice_name: str) -> Dict[str, Any]:
        """Get voice settings (with defaults) for ElevenLabs API."""
        voice_config = self.get_voice_config(voice_name)

        default_settings = {
            "stability": 0.7,
            "similarity_boost": 0.6,
            "style": 0.2,
            "use_speaker_boost": True
        }

        # Override defaults with voice-specific settings
        voice_settings = voice_config.get("settings", {})
        default_settings.update(voice_settings)

        return default_settings

    def get_voice_model(self, voice_name: str) -> str:
        """Get the ElevenLabs model for a voice."""
        return self.get_voice_config(voice_name)["model"]

    def get_voice_id(self, voice_name: str) -> str:
        """Get the ElevenLabs voice ID for a voice."""
        return self.get_voice_config(voice_name)["voice_id"]

    def reload_config(self, config_path: str = "config.yaml"):
        """Reload voice configuration from file (safe replace)."""
        try:
            new_config = load_voice_config(config_path)
            with self._lock:
                self._voices = new_config
            self.logger.info(
                "Reloaded %d voices from configuration", len(self._voices)
            )
        except Exception as e:
            self.logger.error("Failed to reload voice config: %s", str(e))
            raise

    def add_voice(self, name: str, **kwargs):
        """Add a new voice configuration safely."""
        try:
            voice_data = VoiceSchema(**kwargs).model_dump()
        except ValidationError as e:
            self.logger.error("Invalid voice config for %s: %s", name, str(e))
            raise

        with self._lock:
            self._voices[name] = voice_data
        self.logger.info("Added new voice: %s", name)

    def remove_voice(self, name: str):
        """Remove a voice configuration."""
        with self._lock:
            if name not in self._voices:
                raise VoiceNotFoundException(name)
            del self._voices[name]
        self.logger.info("Removed voice: %s", name)


# Global voice manager instance
voice_manager = VoiceManager()
