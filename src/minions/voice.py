"""
MinionVoice - Voice synthesis and management for Minions.

Handles:
- Voice creation via ElevenLabs
- Text-to-speech conversion
- Voice configuration loading
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging
import random
import string
import yaml
import os
import sys

# Add parent paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.minions.api.elevenlabs_api import ElevenLabsAPI, VoiceSettings, VoiceInfo

logger = logging.getLogger(__name__)


# Fun minion name components (inspired by Despicable Me)
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
    """Voice configuration loaded from YAML."""
    description: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    model_id: str = "eleven_multilingual_v2"


class MinionVoice:
    """
    Manages voice synthesis for a Minion.
    
    Creates unique voices using ElevenLabs API and handles
    text-to-speech conversion for phone calls.
    
    Attributes:
        minion_id: ID of the associated minion
        name: Voice/minion name
        description: Voice description
        voice_id: ElevenLabs voice ID
        config: Voice configuration settings
    """
    
    DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "configs"
    
    def __init__(
        self,
        minion_id: str,
        name: Optional[str] = None,
        voice_id: Optional[str] = None,
        config: Optional[Dict] = None,
        elevenlabs: Optional[ElevenLabsAPI] = None,
    ):
        """
        Initialize MinionVoice.
        
        Args:
            minion_id: ID of the associated minion.
            name: Voice/minion name.
            voice_id: ElevenLabs voice ID if already created.
            config: Voice configuration dict.
            elevenlabs: ElevenLabs API instance.
        """
        self.minion_id = minion_id
        self.name = name
        self.voice_id = voice_id
        self.config = config or {}
        self.description = self.config.get("description", "")
        self._elevenlabs = elevenlabs or ElevenLabsAPI()
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        minion_name: str,
        config: Optional[Dict] = None,
        elevenlabs: Optional[ElevenLabsAPI] = None,
    ) -> 'MinionVoice':
        """
        Create a new MinionVoice with a unique voice.
        
        This creates a new voice using ElevenLabs Voice Design API
        based on the provided configuration.
        
        Args:
            minion_id: ID of the associated minion.
            minion_name: Name for the minion/voice.
            config: Voice configuration dict. Loads from YAML if not provided.
            elevenlabs: ElevenLabs API instance.
            
        Returns:
            Initialized MinionVoice with created voice.
        """
        voice = cls(minion_id, elevenlabs=elevenlabs)
        
        # Load configuration
        voice.load_config(config)
        
        # Create the voice name
        voice.create_name(minion_name)
        
        # Design and create the voice with ElevenLabs
        voice._create_voice()
        
        return voice
    
    @classmethod
    def load(
        cls,
        minion_id: str,
        voice_info: Dict,
        elevenlabs: Optional[ElevenLabsAPI] = None,
    ) -> 'MinionVoice':
        """
        Load an existing MinionVoice from stored data.
        
        Args:
            minion_id: ID of the associated minion.
            voice_info: Dict with voice data from MinionMemory.
            elevenlabs: ElevenLabs API instance.
            
        Returns:
            Loaded MinionVoice instance.
        """
        return cls(
            minion_id=minion_id,
            name=voice_info.get("voice_name"),
            voice_id=voice_info.get("voice_id"),
            config=voice_info.get("voice_config", {}),
            elevenlabs=elevenlabs,
        )
    
    def load_config(self, config: Optional[Dict] = None) -> None:
        """
        Load voice configuration.
        
        If config is provided, uses it directly. Otherwise loads
        the first available YAML config file.
        
        Args:
            config: Optional configuration dict.
        """
        if config:
            self.config = config
            self.description = config.get("description", "")
            return
        
        # Try to load from YAML files
        config_dir = self.DEFAULT_CONFIG_DIR
        if config_dir.exists():
            for yaml_file in config_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, "r") as f:
                        all_configs = yaml.safe_load(f)
                    
                    # Use 'default' config if available, otherwise first config
                    if "default" in all_configs:
                        self.config = all_configs["default"]
                    else:
                        self.config = next(iter(all_configs.values()))
                    
                    self.description = self.config.get("description", "")
                    logger.info("Loaded voice config from %s", yaml_file)
                    return
                except Exception as e:
                    logger.warning("Failed to load config from %s: %s", yaml_file, e)
        
        # Fallback to default config
        self.config = {
            "description": "A friendly, helpful assistant voice.",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "model_id": "eleven_multilingual_v2",
        }
        self.description = self.config["description"]
        logger.info("Using default voice config")
    
    def create_name(self, minion_name: str) -> str:
        """
        Create a unique voice name.
        
        Args:
            minion_name: Base name for the minion.
            
        Returns:
            Generated unique name.
        """
        if minion_name:
            self.name = minion_name
        else:
            # Generate a fun minion name
            prefix = random.choice(MINION_NAME_PREFIXES)
            suffix = random.choice(MINION_NAME_SUFFIXES)
            unique_id = ''.join(random.choices(string.digits, k=3))
            self.name = f"{prefix}-{suffix}-{unique_id}"
        
        logger.info("Created minion voice name: %s", self.name)
        return self.name
    
    def _create_voice(self) -> None:
        """Create the voice using ElevenLabs API."""
        # First, design the voice based on description
        description = self.config.get("description", self.description)
        generated_id = self._elevenlabs.design_voice(description)
        
        # Then create a permanent voice from the design
        voice_info = self._elevenlabs.create_voice(
            name=self.name,
            description=description,
            generated_voice_id=generated_id,
        )
        
        self.voice_id = voice_info.voice_id
        logger.info("Created ElevenLabs voice with ID: %s", self.voice_id)
    
    def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert.
            
        Returns:
            Audio data as bytes (MP3 format).
        """
        if not self.voice_id:
            logger.warning("No voice ID set, cannot generate speech")
            return b""
        
        settings = VoiceSettings(
            stability=self.config.get("stability", 0.5),
            similarity_boost=self.config.get("similarity_boost", 0.75),
            style=self.config.get("style", 0.0),
            use_speaker_boost=self.config.get("use_speaker_boost", True),
        )
        
        return self._elevenlabs.text_to_speech(
            text=text,
            voice_id=self.voice_id,
            settings=settings,
            model_id=self.config.get("model_id", "eleven_multilingual_v2"),
        )
    
    async def text_to_speech_async(self, text: str) -> bytes:
        """
        Async version of text_to_speech().
        
        Args:
            text: Text to convert.
            
        Returns:
            Audio data as bytes (MP3 format).
        """
        if not self.voice_id:
            logger.warning("No voice ID set, cannot generate speech")
            return b""
        
        settings = VoiceSettings(
            stability=self.config.get("stability", 0.5),
            similarity_boost=self.config.get("similarity_boost", 0.75),
            style=self.config.get("style", 0.0),
            use_speaker_boost=self.config.get("use_speaker_boost", True),
        )
        
        return await self._elevenlabs.text_to_speech_async(
            text=text,
            voice_id=self.voice_id,
            settings=settings,
            model_id=self.config.get("model_id", "eleven_multilingual_v2"),
        )
    
    def speech_to_text(self, audio: bytes) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio data as bytes.
            
        Returns:
            Transcribed text.
        """
        return self._elevenlabs.speech_to_text(audio)
    
    def to_dict(self) -> Dict:
        """Convert voice to dictionary for storage."""
        return {
            "minion_id": self.minion_id,
            "voice_name": self.name,
            "voice_id": self.voice_id,
            "voice_description": self.description,
            "voice_config": self.config,
        }
    
    def delete(self) -> bool:
        """
        Delete the voice from ElevenLabs.
        
        Returns:
            True if deleted successfully.
        """
        if self.voice_id:
            return self._elevenlabs.delete_voice(self.voice_id)
        return False
