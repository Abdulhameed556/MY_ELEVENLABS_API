import pytest

from app.services.elevenlabs_service import ElevenLabsTTSService
from app.middleware.error_handler import (
    ElevenLabsException,
    ValidationException,
)


@pytest.mark.asyncio
async def test_text_too_long_raises(monkeypatch):
    svc = ElevenLabsTTSService()

    # Voice available
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

    long_text = "x" * (10001)
    with pytest.raises(ValidationException):
        await svc.text_to_speech(
            text=long_text,
            voice_name="test",
            news_id="n1",
            request_id="r1",
        )

    await svc.aclose()


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        json_data=None,
        headers=None,
        content=b"",
    ):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.content = content
        self.text = ""

    def json(self):
        return self._json


@pytest.mark.asyncio
async def test_get_voices_unauthorized(monkeypatch):
    svc = ElevenLabsTTSService()

    async def fake_get(_url):
        return FakeResponse(status_code=401)

    monkeypatch.setattr(svc.client, "get", fake_get)

    with pytest.raises(ElevenLabsException):
        await svc.get_voices()

    await svc.aclose()


@pytest.mark.asyncio
async def test_generate_chunk_retries_then_fails(monkeypatch):
    svc = ElevenLabsTTSService()

    # Patch backoff to no-op
    async def no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(svc, "_sleep_backoff", no_sleep)

    attempts = {"count": 0}

    async def fake_post(_url, **_kwargs):
        attempts["count"] += 1
        # Always return 500
        return FakeResponse(status_code=500)

    monkeypatch.setattr(svc.client, "post", fake_post)

    with pytest.raises(ElevenLabsException):
        await svc._generate_chunk(
            chunk="hello",
            voice_id="v1",
            model_id="m1",
            voice_settings={"stability": 0.5},
            fmt="mp3",
            chunk_index=1,
        )

    assert attempts["count"] == svc.max_retries

    await svc.aclose()
