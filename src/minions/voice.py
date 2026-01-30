"""
MinionVoice - Voice synthesis and management via ElevenLabs.

Includes name generation from Victor's implementation (vgh workspace).
"""

import logging
import os
import random
import string
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml

from .api import ElevenLabsAPI, VoiceSettings

logger = logging.getLogger(__name__)


# Fun minion name components (inspired by Despicable Me) - from Victor's implementation
MINION_NAME_PREFIXES = [
    "Bello", "Poopaye", "Tank", "Bee", "Papoy",
    "Tulaliloo", "Bananaaaa", "Gelato", "Kampai", "Stupa",
]

MINION_NAME_SUFFIXES = [
    "Bob", "Kevin", "Stuart", "Dave", "Jerry",
    "Phil", "Tim", "Mark", "Carl", "Tom",
]


@dataclass
class VoiceConfig:
    """Configuration for a minion voice."""
    description: str
    model_id: str = "eleven_monolingual_v1"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


class MinionVoice:
    """
    Manages voice synthesis for a Minion using ElevenLabs.
    
    Creates unique voices for each minion and handles text-to-speech
    and speech-to-text operations.
    """
    
    DEFAULT_VOICE_DESCRIPTION = """A friendly, helpful assistant voice. 
    Clear and articulate, with a warm tone. 
    Speaks at a moderate pace with good enunciation."""
    
    def __init__(
        self,
        minion_id: str,
        minion_name: str,
        voice_id: Optional[str] = None,
        config: Optional[VoiceConfig] = None,
        elevenlabs_api: Optional[ElevenLabsAPI] = None,
    ):
        self.minion_id = minion_id
        self.minion_name = minion_name
        self.voice_id = voice_id
        self.config = config or VoiceConfig(description=self.DEFAULT_VOICE_DESCRIPTION)
        self._api = elevenlabs_api or ElevenLabsAPI()
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        minion_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> 'MinionVoice':
        """
        Initialize a new MinionVoice and create the voice in ElevenLabs.
        
        Args:
            minion_id: Unique minion identifier.
            minion_name: Name for the minion (used in voice name).
            config: Optional voice configuration dict.
            
        Returns:
            Initialized MinionVoice.
        """
        # Load or create config
        voice_config = cls._load_config(config)
        
        voice = cls(
            minion_id=minion_id,
            minion_name=minion_name,
            config=voice_config,
        )
        
        # Create the voice in ElevenLabs
        if voice._api.is_configured:
            voice._create_voice()
        else:
            logger.warning("ElevenLabs not configured, using default voice")
        
        return voice
    
    @classmethod
    def load(
        cls,
        minion_id: str,
        voice_info: Dict[str, Any],
    ) -> 'MinionVoice':
        """
        Load an existing MinionVoice from stored data.
        
        Args:
            minion_id: Unique minion identifier.
            voice_info: Dict with voice data from storage.
            
        Returns:
            Loaded MinionVoice.
        """
        return cls(
            minion_id=minion_id,
            minion_name=voice_info.get('name', 'Unknown'),
            voice_id=voice_info.get('voice_id'),
            config=VoiceConfig(
                description=voice_info.get('description', cls.DEFAULT_VOICE_DESCRIPTION),
                model_id=voice_info.get('model_id', 'eleven_monolingual_v1'),
            ),
        )
    
    @classmethod
    def _load_config(cls, config_dict: Optional[Dict[str, Any]] = None) -> VoiceConfig:
        """Load voice config from dict or find YAML file."""
        if config_dict:
            return VoiceConfig(
                description=config_dict.get('description', cls.DEFAULT_VOICE_DESCRIPTION),
                model_id=config_dict.get('model_id', 'eleven_monolingual_v1'),
                stability=config_dict.get('stability', 0.5),
                similarity_boost=config_dict.get('similarity_boost', 0.75),
                style=config_dict.get('style', 0.0),
                use_speaker_boost=config_dict.get('use_speaker_boost', True),
            )
        
        # Try to load from configs directory
        config_paths = [
            'configs/voice_config.yaml',
            'config/voice.yaml',
            '../configs/voice_config.yaml',
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data:
                            return VoiceConfig(
                                description=data.get('description', cls.DEFAULT_VOICE_DESCRIPTION),
                                model_id=data.get('model_id', 'eleven_monolingual_v1'),
                            )
                except Exception as e:
                    logger.warning(f"Failed to load voice config from {path}: {e}")
        
        return VoiceConfig(description=cls.DEFAULT_VOICE_DESCRIPTION)
    
    def _create_voice(self) -> bool:
        """Create the voice in ElevenLabs."""
        try:
            # First, try to design a unique voice
            generated_id = self._api.design_voice(self.config.description)
            
            # Create the voice with a name
            voice_name = f"Minion-{self.minion_name}"
            voice_info = self._api.create_voice(
                name=voice_name,
                description=self.config.description,
                generated_voice_id=generated_id,
            )
            
            if voice_info:
                self.voice_id = voice_info.voice_id
                logger.info("Created voice %s for minion %s", self.voice_id, self.minion_id)
                return True
            
            # Fallback: use first available voice
            voices = self._api.get_voices()
            if voices:
                self.voice_id = voices[0].voice_id
                logger.info("Using default voice %s for minion %s", self.voice_id, self.minion_id)
                return True
            
            return False
        except Exception as e:
            logger.error("Failed to create voice: %s", e)
            return False
    
    def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to speak.
            
        Returns:
            Audio bytes (MP3 format), or empty bytes on error.
        """
        if not self.voice_id:
            logger.warning("No voice ID configured")
            return b""
        
        audio = self._api.text_to_speech(
            text=text,
            voice_id=self.voice_id,
            model_id=self.config.model_id,
        )
        
        return audio or b""
    
    def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe speech audio to text.
        
        Args:
            audio_data: Audio bytes to transcribe.
            
        Returns:
            Transcribed text, or None on error.
        """
        return self._api.speech_to_text(audio_data)
    
    # Added from Victor's implementation (vgh workspace)
    async def text_to_speech_async(self, text: str) -> bytes:
        """
        Async version of text_to_speech().
        
        Args:
            text: Text to speak.
            
        Returns:
            Audio bytes (MP3 format).
        """
        if not self.voice_id:
            logger.warning("No voice ID configured")
            return b""
        
        settings = VoiceSettings(
            stability=self.config.stability,
            similarity_boost=self.config.similarity_boost,
            style=self.config.style,
            use_speaker_boost=self.config.use_speaker_boost,
        )
        
        return await self._api.text_to_speech_async(
            text=text,
            voice_id=self.voice_id,
            settings=settings,
            model_id=self.config.model_id,
        )
    
    def delete(self) -> bool:
        """
        Delete the voice from ElevenLabs.
        
        Returns:
            True if deleted successfully.
        """
        if self.voice_id:
            return self._api.delete_voice(self.voice_id)
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize voice to dictionary for storage."""
        return {
            'minion_id': self.minion_id,
            'name': self.minion_name,
            'voice_id': self.voice_id,
            'description': self.config.description,
            'model_id': self.config.model_id,
            'voice_config': {
                'stability': self.config.stability,
                'similarity_boost': self.config.similarity_boost,
                'style': self.config.style,
                'use_speaker_boost': self.config.use_speaker_boost,
            },
        }
    
    @staticmethod
    def generate_name() -> str:
        """
        Generate a fun minion name.
        
        Returns:
            Generated name like "Bello-Bob-123" or "Papoy-Kevin-456".
        """
        prefix = random.choice(MINION_NAME_PREFIXES)
        suffix = random.choice(MINION_NAME_SUFFIXES)
        unique_id = ''.join(random.choices(string.digits, k=3))
        return f"{prefix}-{suffix}-{unique_id}"
