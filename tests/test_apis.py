"""
Tests for API clients.

Tests OpenAIAPI, ElevenLabsAPI, and TwilioAPI in mock mode.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.minions.api.openai_api import OpenAIAPI, CompletionResult
from src.minions.api.elevenlabs_api import ElevenLabsAPI, VoiceInfo, VoiceSettings
from src.minions.api.twilio_api import TwilioAPI, CallInfo, CallStatus


class TestOpenAIAPI:
    """Tests for OpenAI API client."""
    
    def test_init_without_key(self):
        """Test initialization without API key uses mock mode."""
        api = OpenAIAPI(api_key=None)
        assert not api._is_available()
    
    def test_init_with_key(self):
        """Test initialization with API key."""
        api = OpenAIAPI(api_key="test-key")
        # Still won't be available if openai package not installed
        # but key should be stored
        assert api.api_key == "test-key"
    
    def test_complete_mock_mode(self):
        """Test completion in mock mode."""
        api = OpenAIAPI(api_key=None)
        result = api.complete([{"role": "user", "content": "Hello"}])
        
        assert isinstance(result, CompletionResult)
        assert "Mock response" in result.content
        assert result.finish_reason == "stop"
    
    def test_complete_with_system_prompt(self):
        """Test completion with system prompt in mock mode."""
        api = OpenAIAPI(api_key=None)
        result = api.complete(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="You are helpful",
        )
        
        assert isinstance(result, CompletionResult)
    
    def test_summarize_mock_mode(self):
        """Test summarization in mock mode."""
        api = OpenAIAPI(api_key=None)
        result = api.summarize("This is a test conversation.")
        
        assert isinstance(result, str)
        assert "Mock response" in result
    
    def test_summarize_different_styles(self):
        """Test summarization with different styles."""
        api = OpenAIAPI(api_key=None)
        
        for style in ["concise", "detailed", "bullet"]:
            result = api.summarize("Test text", style=style)
            assert isinstance(result, str)
    
    def test_process_instruction_mock_mode(self):
        """Test instruction processing in mock mode."""
        api = OpenAIAPI(api_key=None)
        result = api.process_instruction("stop the current task")
        
        assert isinstance(result, dict)
        assert "action" in result or "response" in result
    
    def test_model_configuration(self):
        """Test model configuration."""
        api = OpenAIAPI(model="gpt-4", max_tokens=1000)
        
        assert api.model == "gpt-4"
        assert api.max_tokens == 1000


class TestElevenLabsAPI:
    """Tests for ElevenLabs API client."""
    
    def test_init_without_key(self):
        """Test initialization without API key uses mock mode."""
        api = ElevenLabsAPI(api_key=None)
        assert not api._is_available()
    
    def test_init_with_key(self):
        """Test initialization with API key."""
        api = ElevenLabsAPI(api_key="test-key")
        assert api.api_key == "test-key"
    
    def test_design_voice_mock_mode(self):
        """Test voice design in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.design_voice("A friendly voice")
        
        assert isinstance(result, str)
        assert result == "mock_generated_voice_id"
    
    def test_create_voice_mock_mode(self):
        """Test voice creation in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.create_voice(
            name="Test Voice",
            description="A test voice",
            generated_voice_id="mock_id",
        )
        
        assert isinstance(result, VoiceInfo)
        assert result.name == "Test Voice"
        assert result.voice_id == "mock_voice_id"
    
    def test_text_to_speech_mock_mode(self):
        """Test TTS in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.text_to_speech(
            text="Hello world",
            voice_id="test_voice",
        )
        
        assert isinstance(result, bytes)
        assert result == b""  # Empty bytes in mock mode
    
    def test_text_to_speech_with_settings(self):
        """Test TTS with custom settings."""
        api = ElevenLabsAPI(api_key=None)
        settings = VoiceSettings(stability=0.8, similarity_boost=0.9)
        
        result = api.text_to_speech(
            text="Hello",
            voice_id="test",
            settings=settings,
        )
        
        assert isinstance(result, bytes)
    
    def test_speech_to_text_mock_mode(self):
        """Test STT in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.speech_to_text(b"audio_data")
        
        assert isinstance(result, str)
        assert "placeholder" in result.lower() or "transcription" in result.lower()
    
    def test_get_voices_mock_mode(self):
        """Test getting voices in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.get_voices()
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], VoiceInfo)
    
    def test_delete_voice_mock_mode(self):
        """Test voice deletion in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = api.delete_voice("test_voice_id")
        
        assert result is True


class TestTwilioAPI:
    """Tests for Twilio API client."""
    
    def test_init_without_credentials(self):
        """Test initialization without credentials uses mock mode."""
        api = TwilioAPI(account_sid=None, auth_token=None)
        assert not api._is_available()
    
    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        api = TwilioAPI(
            account_sid="test_sid",
            auth_token="test_token",
            from_number="+15551234567",
        )
        assert api.account_sid == "test_sid"
        assert api.from_number == "+15551234567"
    
    def test_initiate_call_mock_mode(self):
        """Test call initiation in mock mode."""
        api = TwilioAPI(account_sid=None, auth_token=None)
        result = api.initiate_call(
            to_number="+15559876543",
            webhook_url="https://example.com/webhook",
        )
        
        assert isinstance(result, CallInfo)
        assert result.status == CallStatus.QUEUED
        assert result.to_number == "+15559876543"
    
    def test_get_call_status_mock_mode(self):
        """Test getting call status in mock mode."""
        api = TwilioAPI(account_sid=None, auth_token=None)
        result = api.get_call_status("test_call_sid")
        
        assert isinstance(result, CallInfo)
        assert result.call_sid == "test_call_sid"
        assert result.status == CallStatus.IN_PROGRESS
    
    def test_end_call_mock_mode(self):
        """Test ending call in mock mode."""
        api = TwilioAPI(account_sid=None, auth_token=None)
        result = api.end_call("test_call_sid")
        
        assert isinstance(result, CallInfo)
        assert result.status == CallStatus.COMPLETED
    
    def test_generate_twiml_say(self):
        """Test TwiML generation for Say."""
        api = TwilioAPI()
        twiml = api.generate_twiml_say("Hello, world!")
        
        assert '<?xml version="1.0"' in twiml
        assert "<Response>" in twiml
        assert "<Say" in twiml
        assert "Hello, world!" in twiml
    
    def test_generate_twiml_stream(self):
        """Test TwiML generation for Stream."""
        api = TwilioAPI()
        twiml = api.generate_twiml_stream("wss://example.com/stream")
        
        assert '<?xml version="1.0"' in twiml
        assert "<Connect>" in twiml
        assert "<Stream" in twiml
        assert "wss://example.com/stream" in twiml


@pytest.mark.asyncio
class TestAsyncAPIs:
    """Tests for async API methods."""
    
    async def test_openai_complete_async_mock(self):
        """Test async completion in mock mode."""
        api = OpenAIAPI(api_key=None)
        result = await api.complete_async([{"role": "user", "content": "Hello"}])
        
        assert isinstance(result, CompletionResult)
        assert "Mock response" in result.content
    
    async def test_elevenlabs_tts_async_mock(self):
        """Test async TTS in mock mode."""
        api = ElevenLabsAPI(api_key=None)
        result = await api.text_to_speech_async("Hello", "test_voice")
        
        assert isinstance(result, bytes)
    
    async def test_twilio_initiate_call_async_mock(self):
        """Test async call initiation in mock mode."""
        api = TwilioAPI(account_sid=None, auth_token=None)
        result = await api.initiate_call_async(
            to_number="+15559876543",
            webhook_url="https://example.com/webhook",
        )
        
        assert isinstance(result, CallInfo)
        assert result.status == CallStatus.QUEUED
