"""
Tests for MinionVoice.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.minions.voice import MinionVoice, MINION_NAME_PREFIXES, MINION_NAME_SUFFIXES
from src.minions.api.elevenlabs_api import ElevenLabsAPI, VoiceInfo, VoiceSettings


@pytest.fixture
def mock_elevenlabs():
    """Create a mock ElevenLabs API."""
    api = Mock(spec=ElevenLabsAPI)
    api.design_voice.return_value = "generated_voice_id"
    api.create_voice.return_value = VoiceInfo(
        voice_id="created_voice_id",
        name="Test Voice",
        description="Test description",
    )
    api.text_to_speech.return_value = b"audio_data"
    api.speech_to_text.return_value = "transcribed text"
    api.delete_voice.return_value = True
    return api


class TestMinionVoice:
    """Tests for MinionVoice class."""
    
    def test_init_basic(self):
        """Test basic initialization."""
        voice = MinionVoice(minion_id="test_minion")
        
        assert voice.minion_id == "test_minion"
        assert voice.name is None
        assert voice.voice_id is None
    
    def test_init_with_params(self):
        """Test initialization with all parameters."""
        voice = MinionVoice(
            minion_id="test",
            name="Bob",
            voice_id="voice_123",
            config={"stability": 0.8},
        )
        
        assert voice.name == "Bob"
        assert voice.voice_id == "voice_123"
        assert voice.config["stability"] == 0.8
    
    def test_init_classmethod(self, mock_elevenlabs):
        """Test init() classmethod creates voice."""
        voice = MinionVoice.init(
            minion_id="test",
            minion_name="TestBot",
            elevenlabs=mock_elevenlabs,
        )
        
        assert voice.name == "TestBot"
        assert voice.voice_id == "created_voice_id"
        mock_elevenlabs.design_voice.assert_called_once()
        mock_elevenlabs.create_voice.assert_called_once()
    
    def test_load_classmethod(self):
        """Test load() classmethod restores voice."""
        voice_info = {
            "voice_name": "SavedVoice",
            "voice_id": "saved_voice_id",
            "voice_config": {"stability": 0.6},
        }
        
        voice = MinionVoice.load("minion1", voice_info)
        
        assert voice.name == "SavedVoice"
        assert voice.voice_id == "saved_voice_id"
        assert voice.config["stability"] == 0.6
    
    def test_create_name_with_provided_name(self):
        """Test create_name uses provided name."""
        voice = MinionVoice(minion_id="test")
        name = voice.create_name("CustomName")
        
        assert name == "CustomName"
        assert voice.name == "CustomName"
    
    def test_create_name_generates_name(self):
        """Test create_name generates name when not provided."""
        voice = MinionVoice(minion_id="test")
        name = voice.create_name("")
        
        assert voice.name is not None
        assert len(voice.name) > 0
        # Name should have format like "Prefix-Suffix-123"
        parts = voice.name.split("-")
        assert len(parts) == 3
        assert parts[0] in MINION_NAME_PREFIXES
        assert parts[1] in MINION_NAME_SUFFIXES
    
    def test_load_config_with_dict(self):
        """Test load_config with provided dict."""
        voice = MinionVoice(minion_id="test")
        config = {
            "description": "Custom voice",
            "stability": 0.9,
        }
        
        voice.load_config(config)
        
        assert voice.config["description"] == "Custom voice"
        assert voice.config["stability"] == 0.9
        assert voice.description == "Custom voice"
    
    def test_load_config_fallback(self):
        """Test load_config uses default when no config provided."""
        voice = MinionVoice(minion_id="test")
        voice.load_config(None)
        
        # Should have default config
        assert "description" in voice.config
        assert "stability" in voice.config
    
    def test_text_to_speech(self, mock_elevenlabs):
        """Test text to speech conversion."""
        voice = MinionVoice(
            minion_id="test",
            voice_id="test_voice",
            config={"stability": 0.5, "similarity_boost": 0.75},
            elevenlabs=mock_elevenlabs,
        )
        
        audio = voice.text_to_speech("Hello world")
        
        assert audio == b"audio_data"
        mock_elevenlabs.text_to_speech.assert_called_once()
    
    def test_text_to_speech_no_voice_id(self):
        """Test TTS returns empty bytes when no voice ID."""
        voice = MinionVoice(minion_id="test")
        audio = voice.text_to_speech("Hello")
        
        assert audio == b""
    
    def test_speech_to_text(self, mock_elevenlabs):
        """Test speech to text conversion."""
        voice = MinionVoice(minion_id="test", elevenlabs=mock_elevenlabs)
        text = voice.speech_to_text(b"audio_data")
        
        assert text == "transcribed text"
        mock_elevenlabs.speech_to_text.assert_called_once_with(b"audio_data")
    
    def test_to_dict(self):
        """Test converting voice to dictionary."""
        voice = MinionVoice(
            minion_id="test",
            name="TestVoice",
            voice_id="voice_123",
            config={"stability": 0.5},
        )
        voice.description = "Test description"
        
        data = voice.to_dict()
        
        assert data["minion_id"] == "test"
        assert data["voice_name"] == "TestVoice"
        assert data["voice_id"] == "voice_123"
        assert data["voice_description"] == "Test description"
        assert data["voice_config"]["stability"] == 0.5
    
    def test_delete(self, mock_elevenlabs):
        """Test voice deletion."""
        voice = MinionVoice(
            minion_id="test",
            voice_id="voice_to_delete",
            elevenlabs=mock_elevenlabs,
        )
        
        result = voice.delete()
        
        assert result is True
        mock_elevenlabs.delete_voice.assert_called_once_with("voice_to_delete")
    
    def test_delete_no_voice_id(self):
        """Test delete returns False when no voice ID."""
        voice = MinionVoice(minion_id="test")
        result = voice.delete()
        
        assert result is False


@pytest.mark.asyncio
class TestMinionVoiceAsync:
    """Async tests for MinionVoice."""
    
    async def test_text_to_speech_async(self):
        """Test async TTS."""
        mock_api = Mock(spec=ElevenLabsAPI)
        mock_api.text_to_speech_async = MagicMock(return_value=b"async_audio")
        
        voice = MinionVoice(
            minion_id="test",
            voice_id="test_voice",
            config={},
            elevenlabs=mock_api,
        )
        
        # Mock the async call
        with patch.object(voice._elevenlabs, 'text_to_speech_async', return_value=b"async_audio"):
            audio = await voice.text_to_speech_async("Hello")
        
        assert audio == b"async_audio"
