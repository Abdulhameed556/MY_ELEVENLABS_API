import pytest

from app.main import create_app
from app.services.elevenlabs_service import tts_service


@pytest.mark.asyncio
async def test_lifespan_calls_aclose(monkeypatch):
    # Patch aclose to observe calls
    called = {"v": False}

    async def fake_aclose():
        called["v"] = True

    monkeypatch.setattr(tts_service, "aclose", fake_aclose)

    app = create_app()

    # Use lifespan manually (avoids needing http server)
    # FastAPI supports async with context for lifespan events
    async with app.router.lifespan_context(app):
        pass

    assert called["v"] is True
