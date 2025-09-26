"""
Improved ElevenLabs TTS Service
"""

import time
import asyncio
import random
import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logger import get_logger, log_request_context
from app.services.voice_manager import voice_manager
from app.utils.chunking import chunk_text
from app.utils.audio_utils import combine_audio_chunks
from app.middleware.error_handler import ElevenLabsException, ValidationException
from app.middleware.metrics import metrics


class ElevenLabsTTSService:
    """Production-ready ElevenLabs TTS Service"""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = settings.elevenlabs_base_url.rstrip("/")
        self.logger = get_logger()
        self.default_format = getattr(settings, 'default_format', 'mp3')
        self.chunk_delay = getattr(settings, 'chunk_delay', 0.5)
        self.max_retries = getattr(settings, 'elevenlabs_max_retries', 3)
        self.backoff_base = getattr(settings, 'elevenlabs_backoff_base', 0.5)
        self.backoff_max = getattr(settings, 'elevenlabs_backoff_max', 4.0)

        self.headers = {
            "Accept": f"audio/{self.default_format}",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        # Async HTTP client
        self.client = httpx.AsyncClient(timeout=settings.request_timeout)

    async def get_voices(self) -> Dict[str, Any]:
        """Get available voices from ElevenLabs API with retries."""
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                response = await self.client.get(f"{self.base_url}/voices")

                duration = time.time() - start_time
                metrics.record_elevenlabs_request("voices", duration, response.status_code)

                if response.status_code == 200:
                    self.logger.info("Successfully retrieved voices from ElevenLabs")
                    return response.json()

                # Retry on 429 and 5xx
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    retry_after_hdr = response.headers.get("retry-after")
                    await self._sleep_backoff(attempt, retry_after_hdr)
                    continue

                # Non-retryable
                msg = self._extract_error(response)
                self.logger.error("Error getting voices: %s", msg)
                raise ElevenLabsException(msg, response.status_code)

            except httpx.TimeoutException as e:
                if attempt < self.max_retries:
                    await self._sleep_backoff(attempt)
                    continue
                self.logger.error("Timeout getting voices: %s", str(e))
                raise ElevenLabsException("Request timeout", retryable=True)
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    await self._sleep_backoff(attempt)
                    continue
                self.logger.error("Network error getting voices: %s", str(e))
                raise ElevenLabsException(f"Network error: {str(e)}", retryable=True)

    async def text_to_speech(
        self,
        text: str,
        voice_name: str,
        news_id: str,
        request_id: str,
        chunk_size: Optional[int] = None,
        override_voice_settings: Optional[Dict[str, Any]] = None,
        output_format: Optional[str] = None,
    ) -> bytes:
        """
        Convert text to speech with chunking for long content.
        Supports overrides for voice settings and output format.
        """

        chunk_size = chunk_size or settings.default_chunk_size
        output_format = output_format or self.default_format

        with log_request_context(request_id=request_id, news_id=news_id, voice=voice_name) as logger:
            try:
                # Validate voice
                if not voice_manager.is_voice_available(voice_name):
                    raise ValidationException(f"Voice '{voice_name}' is not available")

                voice_id = voice_manager.get_voice_id(voice_name)
                model_id = voice_manager.get_voice_model(voice_name)
                voice_settings = {**voice_manager.get_voice_settings(voice_name), **(override_voice_settings or {})}

                logger.info(
                    "Starting TTS generation: %d characters",
                    len(text),
                    extra={"chars_count": len(text), "voice_id": voice_id, "model": model_id},
                )

                # Validate text length
                if len(text) > settings.max_text_length:
                    raise ValidationException(
                        f"Text too long: {len(text)} characters (max: {settings.max_text_length})"
                    )

                # Split text into chunks
                chunks = chunk_text(text, chunk_size)
                audio_chunks: List[bytes] = []
                generation_start = time.time()

                # Process chunks sequentially
                for i, chunk in enumerate(chunks, start=1):
                    logger.info(
                        "Processing chunk %d/%d: %d characters",
                        i,
                        len(chunks),
                        len(chunk),
                    )

                    chunk_audio = await self._generate_chunk(chunk, voice_id, model_id, voice_settings, output_format, i)
                    audio_chunks.append(chunk_audio)

                    # Rate limiting delay
                    if i < len(chunks):
                        await asyncio.sleep(self.chunk_delay)

                # Combine audio
                if audio_chunks:
                    combined_audio = combine_audio_chunks(audio_chunks, output_format)

                    total_duration = time.time() - generation_start
                    metrics.record_generation(
                        voice=voice_name,
                        model=model_id,
                        duration=total_duration,
                        chars=len(text),
                        audio_size=len(combined_audio),
                        format=output_format,
                    )

                    logger.info(
                        "TTS generation completed: %d bytes in %.2fs",
                        len(combined_audio),
                        total_duration,
                        extra={
                            "audio_size_bytes": len(combined_audio),
                            "generation_time_ms": int(total_duration * 1000),
                            "chunks_processed": len(chunks),
                        },
                    )
                    return combined_audio
                else:
                    raise ElevenLabsException("No audio chunks were generated")

            except (ValidationException, ElevenLabsException):
                raise
            except Exception as e:
                logger.error("Unexpected error during TTS generation: %s", str(e), exc_info=True)
                raise ElevenLabsException(f"Unexpected error: {str(e)}")

    async def _generate_chunk(
        self,
        chunk: str,
        voice_id: str,
        model_id: str,
        voice_settings: dict,
        fmt: str,
        chunk_index: int,
    ) -> bytes:
        """Generate a single TTS chunk with retry and error handling."""
        data = {"text": chunk, "model_id": model_id, "voice_settings": voice_settings}

        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                response = await self.client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    json=data,
                    headers={**self.headers, "Accept": f"audio/{fmt}"},
                )

                duration = time.time() - start_time
                metrics.record_elevenlabs_request(voice_id, duration, response.status_code)

                if response.status_code == 200:
                    self.logger.info(
                        "Chunk %d completed in %.2fs",
                        chunk_index,
                        duration,
                        extra={"chunk_duration_ms": int(duration * 1000)},
                    )
                    return response.content

                # Retry on 429/5xx
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    msg = self._extract_error(response)
                    self.logger.warning(
                        "Retryable error in chunk %d (status %d): %s",
                        chunk_index,
                        response.status_code,
                        msg,
                    )
                    await self._sleep_backoff(attempt, response.headers.get("retry-after"))
                    continue

                msg = self._extract_error(response)
                self.logger.error("Error in chunk %d: %s", chunk_index, msg)
                raise ElevenLabsException(msg, response.status_code)

            except httpx.TimeoutException as e:
                if attempt < self.max_retries:
                    self.logger.warning("Timeout on chunk %d attempt %d", chunk_index, attempt)
                    await self._sleep_backoff(attempt)
                    continue
                raise ElevenLabsException(
                    f"Request timeout in chunk {chunk_index}", retryable=True
                )
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    self.logger.warning(
                        "Network error on chunk %d attempt %d: %s",
                        chunk_index,
                        attempt,
                        str(e),
                    )
                    await self._sleep_backoff(attempt)
                    continue
                raise ElevenLabsException(
                    f"Network error in chunk {chunk_index}: {str(e)}",
                    retryable=True,
                )

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Try to parse error from JSON or fallback to text."""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return payload.get("detail") or payload.get("error") or response.text
            return response.text
        except Exception:
            return response.text

    async def _sleep_backoff(self, attempt: int, retry_after: Optional[str] = None) -> None:
        """Sleep using exponential backoff with jitter or respect Retry-After header."""
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self.backoff_base
        else:
            delay = min(self.backoff_max, self.backoff_base * (2 ** (attempt - 1)))
            delay += random.uniform(0, self.backoff_base)
        await asyncio.sleep(delay)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()


# Global TTS service instance
tts_service = ElevenLabsTTSService()