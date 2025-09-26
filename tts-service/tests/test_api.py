import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_tts_service():
    with patch('app.api.routes_tts.tts_service') as mock_service:
        mock_service.text_to_speech = AsyncMock(
            return_value=b"mock_audio_data"
        )
        mock_service.get_voices = AsyncMock(
            return_value={
                "voices": [
                    {"voice_id": "test_id", "name": "Test Voice"}
                ]
            }
        )
        yield mock_service


@pytest.fixture
def mock_voice_manager():
    with patch('app.api.routes_tts.voice_manager') as mock_vm:
        mock_vm.is_voice_available.return_value = True
        mock_vm.get_voice_config.return_value = {
            "voice_id": "test_id",
            "model": "test_model",
            "description": "Test voice",
        }
        mock_vm.get_all_voices.return_value = [{
            "voice_id": "test_id",
            "name": "test_voice",
            "description": "Test voice",
            "model": "test_model",
            "category": "test",
            "settings": {"stability": 0.7, "similarity_boost": 0.6}
        }]
        yield mock_vm


class TestTTSAPI:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "service" in response.json()

    def test_health_check(self, mock_tts_service):
        response = client.get("/v1/tts/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_list_voices(self, mock_voice_manager):
        response = client.get("/v1/tts/voices")
        assert response.status_code == 200
        assert "voices" in response.json()

    @pytest.mark.parametrize(
        "payload, expected_status",
        [
            ({"news_id": "test_news_123"}, 422),
            (
                {
                    "news_id": "test_news_123",
                    "title": "",
                    "body": "   ",
                    "voice": "adam",
                },
                422,
            ),
            (
                {
                    "news_id": "test_news_123",
                    "title": "Test",
                    "body": "x" * 15000,
                    "voice": "adam",
                },
                422,
            ),
        ],
    )
    def test_generate_tts_invalid_inputs(
        self, mock_voice_manager, payload, expected_status
    ):
        response = client.post("/v1/tts/generate", json=payload)
        assert response.status_code == expected_status

    def test_metrics_increment(self):
        def sum_metric(text: str, metric: str) -> float:
            total = 0.0
            for line in text.splitlines():
                if line.startswith("#"):
                    continue
                if not line.startswith(metric):
                    continue
                # Example:
                # tts_requests_total{method="GET",route="/v1/tts/voices",
                # status_code="200",voice="unknown"} 1.0
                try:
                    value_str = line.rsplit(" ", 1)[-1]
                    total += float(value_str)
                except Exception:
                    continue
            return total

        before = client.get("/metrics").text
        client.get("/v1/tts/voices")
        after = client.get("/metrics").text
        assert "tts_requests_total" in after
        assert sum_metric(after, "tts_requests_total") > sum_metric(
            before, "tts_requests_total"
        )
