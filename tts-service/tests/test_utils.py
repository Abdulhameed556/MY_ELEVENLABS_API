import pytest

from app.utils.chunking import chunk_text, validate_text_for_tts
from app.utils.audio_utils import combine_audio_chunks, validate_audio_data


def test_chunk_text_short():
    text = "Short text"
    chunks = chunk_text(text, max_length=100)
    assert chunks == [text]


def test_chunk_text_long():
    text = ("This is a long sentence. ") * 50
    chunks = chunk_text(text, max_length=500)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_validate_text_for_tts_valid():
    assert validate_text_for_tts("This is valid") is True


def test_validate_text_for_tts_invalid():
    assert validate_text_for_tts("") is False
    assert validate_text_for_tts("   ") is False
    assert validate_text_for_tts("x" * 15000, max_length=10000) is False


def test_combine_audio_chunks_single():
    assert combine_audio_chunks([b"audio"]) == b"audio"


def test_combine_audio_chunks_empty():
    with pytest.raises(ValueError):
        combine_audio_chunks([])


def test_validate_audio_data_headers():
    # Mock likely MP3 header
    mp3 = b"\xff\xfb" + b"x" * 2000
    assert validate_audio_data(mp3) is True
    assert validate_audio_data(b"") is False
    assert validate_audio_data(b"invalid") is False
    assert validate_audio_data(b"x" * 10) is False
