"""
MinionMemory - Persistent storage for minion state.

Includes key constants and methods from Victor's implementation (vgh workspace).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import RedisDatabase

logger = logging.getLogger(__name__)


@dataclass
class MinionInfo:
    """Stored information about a minion."""
    minion_id: str
    chat_uid: str
    minion_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    voice_description: Optional[str] = None


class MinionMemory:
    """
    Manages persistent storage for a Minion's state.
    
    Stores in Redis:
    - Minion info (ID, name, chat UID)
    - Voice configuration
    - Chat summaries
    """
    
    # Redis key prefixes (from Victor's implementation)
    KEY_PREFIX = "minion:"
    INFO_SUFFIX = ":info"
    VOICE_SUFFIX = ":voice"
    SUMMARIES_SUFFIX = ":summaries"
    
    def __init__(
        self,
        minion_id: str,
        chat_uid: str,
        redis_db: Optional[RedisDatabase] = None,
    ):
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self._redis = redis_db or RedisDatabase()
        
        if not self._redis.is_connected:
            self._redis.connect()
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        chat_uid: str,
        redis_db: Optional[RedisDatabase] = None,
    ) -> 'MinionMemory':
        """
        Initialize MinionMemory and create entry in Redis.
        
        If minion already exists, clears the summaries for a fresh start.
        
        Args:
            minion_id: Unique minion identifier.
            chat_uid: Chat UID being monitored.
            redis_db: Optional Redis database instance.
            
        Returns:
            Initialized MinionMemory.
        """
        memory = cls(minion_id, chat_uid, redis_db)
        
        # Create or update the minion entry
        now = datetime.now()
        
        existing = memory.get_info()
        if existing:
            # Update existing minion
            memory._redis.write(f"minion:{minion_id}", {
                'minion_id': minion_id,
                'chat_uid': chat_uid,
                'minion_name': existing.minion_name,
                'created_at': existing.created_at.isoformat(),
                'updated_at': now.isoformat(),
            })
            # Clear summaries for fresh start
            memory._clear_summaries()
        else:
            # Create new minion entry
            memory._redis.write(f"minion:{minion_id}", {
                'minion_id': minion_id,
                'chat_uid': chat_uid,
                'minion_name': '',  # Will be set via save_name
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
            })
        
        logger.info("MinionMemory initialized for %s", minion_id)
        return memory
    
    def exists(self) -> bool:
        """Check if this minion exists in storage."""
        return self._redis.exists(f"minion:{self.minion_id}")
    
    def get_info(self) -> Optional[MinionInfo]:
        """Get minion info from storage."""
        data = self._redis.read(f"minion:{self.minion_id}")
        if not data:
            return None
        
        return MinionInfo(
            minion_id=data['minion_id'],
            chat_uid=data['chat_uid'],
            minion_name=data.get('minion_name', ''),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
        )
    
    def save_name(self, name: str) -> bool:
        """Save the minion's name."""
        data = self._redis.read(f"minion:{self.minion_id}")
        if data:
            data['minion_name'] = name
            data['updated_at'] = datetime.now().isoformat()
            return self._redis.write(f"minion:{self.minion_id}", data)
        return False
    
    def save_voice(self, voice: Any) -> bool:
        """
        Save voice configuration.
        
        Args:
            voice: MinionVoice instance or dict with voice data.
            
        Returns:
            True if successful.
        """
        if hasattr(voice, 'to_dict'):
            voice_data = voice.to_dict()
        elif isinstance(voice, dict):
            voice_data = voice
        else:
            return False
        
        return self._redis.write(f"minion:{self.minion_id}:voice", voice_data)
    
    def get_voice_info(self) -> Optional[Dict[str, Any]]:
        """Get voice configuration from storage."""
        return self._redis.read(f"minion:{self.minion_id}:voice")
    
    def save_summary(self, summary: str) -> bool:
        """
        Add a summary to the summaries list.
        
        Args:
            summary: Summary text to save.
            
        Returns:
            True if successful.
        """
        return self._redis.list_push(f"minion:{self.minion_id}:summaries", summary)
    
    def get_summaries(self) -> List[str]:
        """Get all summaries for this minion."""
        return self._redis.list_get(f"minion:{self.minion_id}:summaries")
    
    def get_latest_summary(self) -> Optional[str]:
        """Get the most recent summary."""
        summaries = self.get_summaries()
        if summaries:
            return summaries[-1]
        return None
    
    def _clear_summaries(self) -> bool:
        """Clear all summaries."""
        return self._redis.delete(f"minion:{self.minion_id}:summaries")
    
    def delete(self) -> bool:
        """Delete all data for this minion."""
        keys = [
            f"minion:{self.minion_id}",
            f"minion:{self.minion_id}:voice",
            f"minion:{self.minion_id}:summaries",
        ]
        success = True
        for key in keys:
            if not self._redis.delete(key):
                success = False
        return success
    
    # Additional methods from Victor's implementation (vgh workspace)
    
    def update_info(self, **kwargs) -> None:
        """
        Update minion info fields.
        
        Args:
            **kwargs: Fields to update (minion_name, voice_id, etc.)
        """
        data = self._redis.read(f"minion:{self.minion_id}") or {}
        data.update(kwargs)
        data['updated_at'] = datetime.now().isoformat()
        self._redis.write(f"minion:{self.minion_id}", data)
    
    def get_summaries_with_timestamps(self) -> List[Dict]:
        """
        Get all summaries with their timestamps.
        
        Returns:
            List of dicts with 'summary' and 'timestamp' keys.
        """
        return self._redis.list_get(f"minion:{self.minion_id}:summaries")
