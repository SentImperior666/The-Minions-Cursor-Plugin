"""
MinionMemory - State management for Minions.

Handles persistence of minion state including:
- Minion info (ID, chat UID, name)
- Voice configuration
- Chat summaries
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import sys
import os

# Add mocks to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from mocks.redis_mock import RedisDatabase

logger = logging.getLogger(__name__)


@dataclass
class MinionInfo:
    """Information about a minion stored in memory."""
    minion_id: str
    chat_uid: str
    minion_name: str
    created_at: datetime = field(default_factory=datetime.now)
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    voice_description: Optional[str] = None


class MinionMemory:
    """
    Manages minion state in Redis database.
    
    Provides persistence for minion information, voice configuration,
    and chat summaries.
    
    Attributes:
        minion_id: Unique identifier for the minion
        chat_uid: UID of the associated Cursor chat
        _redis: Redis database instance
    """
    
    # Redis key prefixes
    KEY_PREFIX = "minion:"
    INFO_SUFFIX = ":info"
    VOICE_SUFFIX = ":voice"
    SUMMARIES_SUFFIX = ":summaries"
    
    def __init__(
        self,
        minion_id: str,
        chat_uid: str,
        redis: Optional[RedisDatabase] = None,
    ):
        """
        Initialize MinionMemory.
        
        Args:
            minion_id: Unique identifier for the minion.
            chat_uid: UID of the associated Cursor chat.
            redis: Redis database instance. Creates new if not provided.
        """
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self._redis = redis or RedisDatabase()
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        chat_uid: str,
        redis: Optional[RedisDatabase] = None,
    ) -> 'MinionMemory':
        """
        Initialize a new MinionMemory and create database entry.
        
        If a minion with this ID already exists, clears the summaries
        column as per the specification.
        
        Args:
            minion_id: Unique identifier for the minion.
            chat_uid: UID of the associated Cursor chat.
            redis: Optional Redis database instance.
            
        Returns:
            Initialized MinionMemory instance.
        """
        memory = cls(minion_id, chat_uid, redis)
        
        # Check if minion exists
        existing = memory.get_info()
        if existing:
            # Clear summaries for existing minion
            logger.info("Minion %s exists, clearing summaries", minion_id)
            memory._clear_summaries()
        else:
            # Create new minion entry
            logger.info("Creating new minion memory for %s", minion_id)
            memory._create_info_entry()
        
        return memory
    
    def _key(self, suffix: str) -> str:
        """Generate Redis key for this minion with given suffix."""
        return f"{self.KEY_PREFIX}{self.minion_id}{suffix}"
    
    def _create_info_entry(self) -> None:
        """Create the initial info entry for this minion."""
        info = {
            "minion_id": self.minion_id,
            "chat_uid": self.chat_uid,
            "created_at": datetime.now().isoformat(),
        }
        self._redis.write(self._key(self.INFO_SUFFIX), info)
    
    def _clear_summaries(self) -> None:
        """Clear all summaries for this minion."""
        self._redis.write(self._key(self.SUMMARIES_SUFFIX), [])
    
    def get_info(self) -> Optional[MinionInfo]:
        """
        Get minion info from database.
        
        Returns:
            MinionInfo if minion exists, None otherwise.
        """
        data = self._redis.read(self._key(self.INFO_SUFFIX))
        if not data:
            return None
        
        return MinionInfo(
            minion_id=data["minion_id"],
            chat_uid=data["chat_uid"],
            minion_name=data.get("minion_name", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            voice_id=data.get("voice_id"),
            voice_name=data.get("voice_name"),
            voice_description=data.get("voice_description"),
        )
    
    def update_info(self, **kwargs) -> None:
        """
        Update minion info fields.
        
        Args:
            **kwargs: Fields to update (minion_name, voice_id, etc.)
        """
        data = self._redis.read(self._key(self.INFO_SUFFIX)) or {}
        data.update(kwargs)
        self._redis.write(self._key(self.INFO_SUFFIX), data)
    
    def save_name(self, minion_name: str) -> None:
        """
        Save the minion's name.
        
        Args:
            minion_name: Name for the minion.
        """
        self.update_info(minion_name=minion_name)
        logger.info("Saved minion name: %s", minion_name)
    
    def save_voice(self, voice: Any) -> None:
        """
        Persist voice information for this minion.
        
        Stores voice name, description, and ElevenLabs voice ID.
        
        Args:
            voice: MinionVoice instance with voice configuration.
        """
        voice_data = {
            "voice_name": getattr(voice, 'name', None),
            "voice_description": getattr(voice, 'description', None),
            "voice_id": getattr(voice, 'voice_id', None),
            "voice_config": getattr(voice, 'config', {}),
        }
        
        # Update main info
        self.update_info(
            voice_id=voice_data["voice_id"],
            voice_name=voice_data["voice_name"],
            voice_description=voice_data["voice_description"],
        )
        
        # Store full voice config separately
        self._redis.write(self._key(self.VOICE_SUFFIX), voice_data)
        logger.info("Saved voice info for minion %s", self.minion_id)
    
    def get_voice_info(self) -> Dict:
        """
        Get voice configuration for this minion.
        
        Returns:
            Dict with voice configuration, or empty dict if not set.
        """
        return self._redis.read(self._key(self.VOICE_SUFFIX)) or {}
    
    def save_summary(self, summary: str) -> None:
        """
        Add a summary to the minion's summary list.
        
        Args:
            summary: Summary text to add.
        """
        self._redis.list_append(
            self._key(self.SUMMARIES_SUFFIX),
            {
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info("Saved summary for minion %s (%d chars)", self.minion_id, len(summary))
    
    def get_summaries(self) -> List[str]:
        """
        Get all summaries for this minion.
        
        Returns:
            List of summary strings.
        """
        data = self._redis.list_get(self._key(self.SUMMARIES_SUFFIX))
        return [item["summary"] if isinstance(item, dict) else item for item in data]
    
    def get_summaries_with_timestamps(self) -> List[Dict]:
        """
        Get all summaries with their timestamps.
        
        Returns:
            List of dicts with 'summary' and 'timestamp' keys.
        """
        return self._redis.list_get(self._key(self.SUMMARIES_SUFFIX))
    
    def get_latest_summary(self) -> Optional[str]:
        """
        Get the most recent summary.
        
        Returns:
            Latest summary string, or None if no summaries.
        """
        summaries = self.get_summaries()
        return summaries[-1] if summaries else None
    
    def exists(self) -> bool:
        """
        Check if this minion exists in the database.
        
        Returns:
            True if minion exists.
        """
        return self._redis.exists(self._key(self.INFO_SUFFIX))
    
    def delete(self) -> None:
        """Delete all data for this minion from the database."""
        self._redis.delete(self._key(self.INFO_SUFFIX))
        self._redis.delete(self._key(self.VOICE_SUFFIX))
        self._redis.delete(self._key(self.SUMMARIES_SUFFIX))
        logger.info("Deleted all data for minion %s", self.minion_id)
