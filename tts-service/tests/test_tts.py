"""
Unit Tests for TTS Service (legacy)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
pytestmark = pytest.mark.skip(
    reason=(
        "Legacy unit tests target old sync TTS service; skipped until migrated to async/httpx."
    )
)
from app.services.elevenlabs_service import ElevenLabsTTSService
from app.services.voice_manager import VoiceManager
from app.middleware.error_handler import ElevenLabsException, ValidationException
from app.utils.chunking import chunk_text, validate_text_for_tts
from app.utils.audio_utils import combine_audio_chunks, validate_audio_data


class TestElevenLabsTTSService:
    """Test cases for ElevenLabs TTS Service"""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch('app.services.elevenlabs_service.settings') as mock_settings:
            mock_settings.elevenlabs_api_key = "test_key"
            mock_settings.elevenlabs_base_url = "https://api.test.com/v1"
            mock_settings.request_timeout = 30
            mock_settings.max_text_length = 10000
            mock_settings.default_chunk_size = 2500
            yield mock_settings
    
    @pytest.fixture
    def mock_voice_manager(self):
        """Mock voice manager for testing"""
        with patch('app.services.elevenlabs_service.voice_manager') as mock_vm:
            mock_vm.is_voice_available.return_value = True
            mock_vm.get_voice_id.return_value = "test_voice_id"
            mock_vm.get_voice_model.return_value = "eleven_turbo_v2_5"
            mock_vm.get_voice_settings.return_value = {
                "stability": 0.7,
                "similarity_boost": 0.6
            }
            yield mock_vm
    
    @pytest.fixture
    def tts_service(self, mock_settings):
        """Create TTS service instance for testing"""
        return ElevenLabsTTSService()
    
    def test_init(self, tts_service, mock_settings):
        """Test TTS service initialization"""
        assert tts_service.api_key == "test_key"
        assert tts_service.base_url == "https://api.test.com/v1"
        assert "xi-api-key" in tts_service.headers
    
    @patch('app.services.elevenlabs_service.requests.get')
    def test_get_voices_success(self, mock_get, tts_service):
        """Test successful voice retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"voices": []}
        mock_get.return_value = mock_response
        
        result = tts_service.get_voices()
        
        assert result == {"voices": []}
        mock_get.assert_called_once()
    
    @patch('app.services.elevenlabs_service.requests.get')
    def test_get_voices_error(self, mock_get, tts_service):
        """Test voice retrieval error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(ElevenLabsException):
            tts_service.get_voices()
    
    @patch('app.services.elevenlabs_service.chunk_text')
    @patch('app.services.elevenlabs_service.combine_audio_chunks')
    @patch('app.services.elevenlabs_service.requests.post')
    def test_text_to_speech_success(self, mock_post, mock_combine, mock_chunk, 
                                   tts_service, mock_voice_manager):
        """Test successful TTS generation"""
        # Setup mocks
        mock_chunk.return_value = ["test text chunk"]
        mock_combine.return_value = b"combined_audio_data"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"audio_data"
        mock_post.return_value = mock_response
        
        # Test
        result = tts_service.text_to_speech(
            text="Test text",
            voice_name="test_voice",
            news_id="news_123",
            request_id="req_123"
        )
        
        # Assertions
        assert result == b"combined_audio_data"
        mock_voice_manager.is_voice_available.assert_called_with("test_voice")
        mock_post.assert_called_once()
    
    def test_text_to_speech_invalid_voice(self, tts_service, mock_voice_manager):
        """Test TTS with invalid voice"""
        mock_voice_manager.is_voice_available.return_value = False
        
        with pytest.raises(ValidationException):
            tts_service.text_to_speech(
                text="Test text",
                voice_name="invalid_voice",
                news_id="news_123",
                request_id="req_123"
            )


class TestVoiceManager:
    """Test cases for Voice Manager"""
    
    @pytest.fixture
    def voice_config(self):
        """Sample voice configuration"""
        return {
            "test_voice": {
                "voice_id": "test_id",
                "model": "test_model",
                "description": "Test Voice",
                "category": "test",
                "settings": {"stability": 0.5}
            }
        }
    
    @patch('app.services.voice_manager.load_voice_config')
    def test_init(self, mock_load_config, voice_config):
        """Test voice manager initialization"""
        mock_load_config.return_value = voice_config
        
        vm = VoiceManager()
        
        assert vm._voices == voice_config
        mock_load_config.assert_called_once()
    
    @patch('app.services.voice_manager.load_voice_config')
    def test_get_voice_config(self, mock_load_config, voice_config):
        """Test getting voice configuration"""
        mock_load_config.return_value = voice_config
        
        vm = VoiceManager()
        config = vm.get_voice_config("test_voice")
        
        assert config == voice_config["test_voice"]
    
    @patch('app.services.voice_manager.load_voice_config')
    def test_get_voice_config_not_found(self, mock_load_config, voice_config):
        """Test getting non-existent voice configuration"""
        mock_load_config.return_value = voice_config
        
        vm = VoiceManager()
        
        with pytest.raises(Exception):  # Should be VoiceNotFoundException
            vm.get_voice_config("nonexistent_voice")


class TestChunking:
    """Test cases for text chunking utilities"""
    
    def test_chunk_text_short(self):
        """Test chunking of short text"""
        text = "Short text"
        chunks = chunk_text(text, max_length=100)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_long(self):
        """Test chunking of long text"""
        text = "This is a long sentence. " * 50  # ~1250 characters
        chunks = chunk_text(text, max_length=500)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 500
    
    def test_validate_text_for_tts_valid(self):
        """Test text validation - valid text"""
        text = "This is valid text for TTS processing."
        
        assert validate_text_for_tts(text) is True
    
    def test_validate_text_for_tts_empty(self):
        """Test text validation - empty text"""
        assert validate_text_for_tts("") is False
        assert validate_text_for_tts("   ") is False
    
    def test_validate_text_for_tts_too_long(self):
        """Test text validation - text too long"""
        text = "x" * 15000
        
        assert validate_text_for_tts(text, max_length=10000) is False


class TestAudioUtils:
    """Test cases for audio utilities"""
    
    def test_combine_audio_chunks_single(self):
        """Test combining single audio chunk"""
        chunks = [b"audio_data"]
        
        result = combine_audio_chunks(chunks)
        
        assert result == b"audio_data"
    
    def test_combine_audio_chunks_empty(self):
        """Test combining empty audio chunks"""
        with pytest.raises(ValueError):
            combine_audio_chunks([])
    
    def test_validate_audio_data_valid(self):
        """Test audio data validation - valid MP3"""
        # Mock MP3 header
        audio_data = b'\xff\xfb' + b'x' * 2000
        
        assert validate_audio_data(audio_data) is True
    
    def test_validate_audio_data_invalid(self):
        """Test audio data validation - invalid data"""
        assert validate_audio_data(b"") is False
        assert validate_audio_data(b"invalid") is False
        assert validate_audio_data(b"x" * 10) is False  # Too small