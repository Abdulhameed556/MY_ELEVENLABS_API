import pytest

from app.services.elevenlabs_service import ElevenLabsTTSService
from app.middleware.error_handler import ValidationException


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        content=b"",
        json_data=None,
        headers=None,
    ):
        self.status_code = status_code
        self.content = content
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._json


@pytest.mark.asyncio
async def test_text_to_speech_success(monkeypatch):
    svc = ElevenLabsTTSService()

    # Voice manager stubs
    monkeypatch.setattr(
        "app.services.elevenlabs_service.voice_manager.is_voice_available",
        lambda name: True,
    )
    monkeypatch.setattr(
        "app.services.elevenlabs_service.voice_manager.get_voice_id",
        lambda name: "voice_123",
    )
    monkeypatch.setattr(
        "app.services.elevenlabs_service.voice_manager.get_voice_model",
        lambda name: "eleven_turbo_v2_5",
    )
    monkeypatch.setattr(
        "app.services.elevenlabs_service.voice_manager.get_voice_settings",
        lambda name: {"stability": 0.6, "similarity_boost": 0.7},
    )

    # Chunking + audio utils
    monkeypatch.setattr(
        "app.services.elevenlabs_service.chunk_text",
        lambda text, max_length: [text],
    )
    monkeypatch.setattr(
        "app.services.elevenlabs_service.combine_audio_chunks",
        lambda chunks, fmt="mp3": b"".join(chunks),
    )

    # HTTP client post
    async def fake_post(_url, _json=None, _headers=None, **_kwargs):
        return FakeResponse(status_code=200, content=b"audio_chunk")

    monkeypatch.setattr(svc.client, "post", fake_post)

    audio = await svc.text_to_speech(
        text="hello world",
        voice_name="test",
        news_id="n1",
        request_id="r1",
    )

    assert audio == b"audio_chunk"
    await svc.aclose()


@pytest.mark.asyncio
async def test_text_to_speech_invalid_voice(monkeypatch):
    svc = ElevenLabsTTSService()

    monkeypatch.setattr(
        "app.services.elevenlabs_service.voice_manager.is_voice_available",
        lambda name: False,
    )

    with pytest.raises(ValidationException):
        await svc.text_to_speech(
            text="hello",
            voice_name="invalid",
            news_id="n1",
            request_id="r1",
        )

    await svc.aclose()


@pytest.mark.asyncio
async def test_get_voices_retry_then_success(monkeypatch):
    svc = ElevenLabsTTSService()

    # Avoid actual sleep
    async def no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(svc, "_sleep_backoff", no_sleep)

    # Simulate 429 then 200
    calls = []

    async def fake_get(url):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(status_code=429, headers={"retry-after": "0"})
        return FakeResponse(status_code=200, json_data={"voices": []})

    monkeypatch.setattr(svc.client, "get", fake_get)

    data = await svc.get_voices()
    assert data == {"voices": []}
    assert len(calls) == 2

    await svc.aclose()
