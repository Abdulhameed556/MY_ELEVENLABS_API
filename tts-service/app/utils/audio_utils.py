"""
Audio Processing Utilities - Production Ready
"""

import io
from typing import List, Dict, Any
from app.core.logger import get_logger

try:
    from pydub import AudioSegment  # type: ignore
    HAS_PYDUB = True
except Exception:
    # On Python 3.13, audioop was removed; pydub may import pyaudioop which may be unavailable.
    # We gracefully degrade to simple concatenation and minimal metadata.
    AudioSegment = None  # type: ignore
    HAS_PYDUB = False


logger = get_logger()

SUPPORTED_FORMATS = {"mp3", "wav", "ogg"}


def combine_audio_chunks(audio_chunks: List[bytes], format: str = "mp3") -> bytes:
    """
    Combine multiple audio chunks into a single audio stream.
    Supports MP3, WAV, OGG.
    """
    if not audio_chunks:
        raise ValueError("No audio chunks provided")

    if len(audio_chunks) == 1:
        return audio_chunks[0]

    if format.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {format}. Must be one of {SUPPORTED_FORMATS}")

    logger.info(f"Combining {len(audio_chunks)} audio chunks into {format.upper()}")

    if not HAS_PYDUB:
        logger.warning(
            "pydub not available; falling back to simple byte concatenation for audio combine"
        )
        return b"".join(audio_chunks)

    try:
        # Load first chunk
        combined = AudioSegment.from_file(io.BytesIO(audio_chunks[0]), format="mp3")

        # Append remaining chunks
        for i, chunk in enumerate(audio_chunks[1:], 1):
            audio_segment = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
            combined += audio_segment
            logger.debug(f"Combined chunk {i+1}/{len(audio_chunks)}")

        # Export to final format
        with io.BytesIO() as output_buffer:
            combined.export(output_buffer, format=format.lower())
            output_buffer.seek(0)
            combined_bytes = output_buffer.read()

        logger.info(f"✅ Successfully combined audio ({len(combined_bytes)} bytes)")
        return combined_bytes

    except Exception as e:
        logger.error(f"Failed to combine audio chunks: {e}", exc_info=True)
        logger.warning("⚠️ Falling back to simple byte concatenation (may produce invalid audio)")
        return b"".join(audio_chunks)


def get_audio_info(audio_data: bytes, source_format: str = "mp3") -> Dict[str, Any]:
    """
    Extract information about audio data.
    Returns duration, frame rate, channels, etc.
    """
    if not HAS_PYDUB:
        return {
            "duration_seconds": None,
            "frame_rate": None,
            "channels": None,
            "sample_width": None,
            "size_bytes": len(audio_data),
            "format": source_format,
        }

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=source_format)
        return {
            "duration_seconds": round(len(audio) / 1000.0, 2),
            "frame_rate": audio.frame_rate,
            "channels": audio.channels,
            "sample_width": audio.sample_width,
            "size_bytes": len(audio_data),
            "format": source_format
        }
    except Exception as e:
        logger.error(f"Failed to extract audio info: {e}", exc_info=True)
        return {
            "duration_seconds": None,
            "frame_rate": None,
            "channels": None,
            "sample_width": None,
            "size_bytes": len(audio_data),
            "format": source_format
        }


def convert_audio_format(audio_data: bytes, target_format: str, source_format: str = "mp3") -> bytes:
    """
    Convert audio from one format to another.
    """
    if target_format.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported target format: {target_format}. Must be {SUPPORTED_FORMATS}")

    if not HAS_PYDUB:
        if target_format.lower() == source_format.lower():
            return audio_data
        raise ValueError(
            "Audio format conversion requires pydub/ffmpeg; not available in this environment"
        )

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=source_format.lower())
        with io.BytesIO() as output_buffer:
            audio.export(output_buffer, format=target_format.lower())
            output_buffer.seek(0)
            return output_buffer.read()
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise ValueError(f"Failed to convert audio from {source_format} to {target_format}: {e}")


def adjust_audio_quality(audio_data: bytes, bitrate: str = "128k", sample_rate: int = 22050) -> bytes:
    """
    Adjust audio quality/compression (bitrate, sample rate).
    Returns modified audio bytes.
    """
    if not HAS_PYDUB:
        # Can't change quality without pydub; return original bytes.
        logger.warning(
            "pydub not available; skipping audio quality adjustment and returning original bytes"
        )
        return audio_data

    try:
        audio = AudioSegment.from_mp3(io.BytesIO(audio_data))

        if audio.frame_rate != sample_rate:
            audio = audio.set_frame_rate(sample_rate)

        with io.BytesIO() as output_buffer:
            audio.export(
                output_buffer,
                format="mp3",
                bitrate=bitrate,
                parameters=["-ar", str(sample_rate)]
            )
            output_buffer.seek(0)
            return output_buffer.read()

    except Exception as e:
        logger.error(f"Audio quality adjustment failed: {e}", exc_info=True)
        raise ValueError(f"Failed to adjust audio quality: {e}")


def validate_audio_data(audio_data: bytes, min_size: int = 1000, max_size: int = 50 * 1024 * 1024) -> bool:
    """
    Validate audio data basic properties (size, format header).
    """
    if not audio_data:
        return False

    if not (min_size <= len(audio_data) <= max_size):
        return False

    # Basic MP3 header check
    if audio_data[:3] == b"ID3" or audio_data[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]:
        return True

    return False