"""
ElevenLabs API client for voice synthesis and transcription.

Provides interface to ElevenLabs API for:
- Voice design (text-to-voice description)
- Voice creation and cloning
- Text-to-speech synthesis
- Speech-to-text transcription
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class VoiceInfo:
    """Information about an ElevenLabs voice."""
    voice_id: str
    name: str
    description: Optional[str] = None
    preview_url: Optional[str] = None


@dataclass
class VoiceSettings:
    """Voice synthesis settings."""
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


class ElevenLabsAPI:
    """
    Interface to ElevenLabs API for voice operations.
    
    Handles voice design, creation, and synthesis for the Minion's
    voice communication capabilities.
    
    Attributes:
        api_key: ElevenLabs API key
        base_url: Base URL for ElevenLabs API
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_MODEL = "eleven_multilingual_v2"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the ElevenLabs API client.
        
        Args:
            api_key: ElevenLabs API key. If not provided, uses ELEVENLABS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        
        if HTTPX_AVAILABLE and self.api_key:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers={"xi-api-key": self.api_key},
                timeout=60.0,
            )
            self._async_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"xi-api-key": self.api_key},
                timeout=60.0,
            )
        else:
            self._client = None
            self._async_client = None
            if not HTTPX_AVAILABLE:
                logger.warning("httpx package not installed. Running in mock mode.")
            elif not self.api_key:
                logger.warning("No ElevenLabs API key provided. Running in mock mode.")
    
    def _is_available(self) -> bool:
        """Check if the ElevenLabs client is available."""
        return self._client is not None
    
    def design_voice(
        self,
        description: str,
        text: str = "Hello! I'm your friendly Minion assistant, ready to help you with your coding tasks.",
    ) -> str:
        """
        Design a new voice based on a text description.
        
        Uses ElevenLabs Voice Design API to generate a voice preview
        from a description.
        
        Args:
            description: Text description of desired voice characteristics.
            text: Sample text to generate with the voice.
            
        Returns:
            Generated voice ID (temporary) for use in create_voice().
        """
        if not self._is_available():
            logger.info("Mock: Designing voice with description: %s", description[:50])
            return "mock_generated_voice_id"
        
        response = self._client.post(
            "/voice-generation/generate-voice",
            json={
                "voice_description": description,
                "text": text,
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("voice_id", "")
    
    def create_voice(
        self,
        name: str,
        description: str,
        generated_voice_id: str,
    ) -> VoiceInfo:
        """
        Create a permanent voice from a generated voice preview.
        
        Args:
            name: Name for the new voice.
            description: Description of the voice.
            generated_voice_id: Voice ID from design_voice().
            
        Returns:
            VoiceInfo with the created voice details.
        """
        if not self._is_available():
            logger.info("Mock: Creating voice '%s' from generated ID: %s", name, generated_voice_id)
            return VoiceInfo(
                voice_id="mock_voice_id",
                name=name,
                description=description,
            )
        
        response = self._client.post(
            "/voice-generation/create-voice",
            json={
                "voice_name": name,
                "voice_description": description,
                "generated_voice_id": generated_voice_id,
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return VoiceInfo(
            voice_id=data.get("voice_id", ""),
            name=name,
            description=description,
        )
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        settings: Optional[VoiceSettings] = None,
        model_id: str = DEFAULT_MODEL,
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech.
            voice_id: ID of the voice to use.
            settings: Voice settings for synthesis.
            model_id: Model ID to use for synthesis.
            
        Returns:
            Audio data as bytes (MP3 format).
        """
        if settings is None:
            settings = VoiceSettings()
        
        if not self._is_available():
            logger.info("Mock: Converting text to speech: %s", text[:50])
            # Return empty bytes as mock audio
            return b""
        
        response = self._client.post(
            f"/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": settings.stability,
                    "similarity_boost": settings.similarity_boost,
                    "style": settings.style,
                    "use_speaker_boost": settings.use_speaker_boost,
                },
            },
        )
        response.raise_for_status()
        
        return response.content
    
    async def text_to_speech_async(
        self,
        text: str,
        voice_id: str,
        settings: Optional[VoiceSettings] = None,
        model_id: str = DEFAULT_MODEL,
    ) -> bytes:
        """
        Async version of text_to_speech().
        
        Args:
            text: Text to convert to speech.
            voice_id: ID of the voice to use.
            settings: Voice settings for synthesis.
            model_id: Model ID to use for synthesis.
            
        Returns:
            Audio data as bytes (MP3 format).
        """
        if settings is None:
            settings = VoiceSettings()
        
        if not self._is_available():
            logger.info("Mock: Converting text to speech async: %s", text[:50])
            return b""
        
        response = await self._async_client.post(
            f"/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": settings.stability,
                    "similarity_boost": settings.similarity_boost,
                    "style": settings.style,
                    "use_speaker_boost": settings.use_speaker_boost,
                },
            },
        )
        response.raise_for_status()
        
        return response.content
    
    def speech_to_text(
        self,
        audio: bytes,
        language_code: str = "en",
    ) -> str:
        """
        Transcribe audio to text.
        
        Note: ElevenLabs doesn't have a native STT API, so this would
        typically use a different service (like OpenAI Whisper).
        This is a placeholder that can be swapped with the actual implementation.
        
        Args:
            audio: Audio data as bytes.
            language_code: Language code for transcription.
            
        Returns:
            Transcribed text.
        """
        # ElevenLabs doesn't have STT - this would use OpenAI Whisper or similar
        logger.info("Mock: Transcribing audio (%d bytes)", len(audio))
        return "[Transcription placeholder - implement with Whisper API]"
    
    def get_voices(self) -> list[VoiceInfo]:
        """
        Get list of available voices.
        
        Returns:
            List of VoiceInfo objects for available voices.
        """
        if not self._is_available():
            return [
                VoiceInfo(voice_id="mock_voice_1", name="Default Voice"),
            ]
        
        response = self._client.get("/voices")
        response.raise_for_status()
        
        data = response.json()
        return [
            VoiceInfo(
                voice_id=v["voice_id"],
                name=v["name"],
                description=v.get("description"),
                preview_url=v.get("preview_url"),
            )
            for v in data.get("voices", [])
        ]
    
    def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a voice.
        
        Args:
            voice_id: ID of the voice to delete.
            
        Returns:
            True if deleted successfully.
        """
        if not self._is_available():
            logger.info("Mock: Deleting voice: %s", voice_id)
            return True
        
        response = self._client.delete(f"/voices/{voice_id}")
        return response.status_code == 200
