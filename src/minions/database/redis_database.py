"""
Redis Database Interface for The Minions Cursor Plugin.

This module provides a clean interface for storing and retrieving data
from a local Redis database. It's used by:
- CursorListener (Task 1): To store chat messages
- MinionMemory (Task 2): To persist minion state, voice data, and summaries
- CodebaseIndexer (Task 3): To store file embeddings
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

import redis
from redis.exceptions import ConnectionError, RedisError

from .data_types import MinionInfo, VoiceData, ChatMessageData

logger = logging.getLogger(__name__)


class RedisDatabaseInterface(ABC):
    """
    Abstract interface for Redis database operations.
    
    This interface allows other components to mock the database
    in their tests without requiring a real Redis instance.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the Redis database."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the Redis database."""
        pass
    
    @abstractmethod
    def write(self, key: str, value: Any) -> bool:
        """Write a value to the database."""
        pass
    
    @abstractmethod
    def read(self, key: str) -> Optional[Any]:
        """Read a value from the database."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from the database."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the database."""
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        pass


class RedisDatabase(RedisDatabaseInterface):
    """
    Redis database implementation for The Minions Cursor Plugin.
    
    Provides operations for storing:
    - Minion info: minion:{minion_id} -> MinionInfo
    - Voice data: minion:{minion_id}:voice -> VoiceData  
    - Summaries: minion:{minion_id}:summaries -> List[str]
    - Chat messages: chat:{chat_uid}:messages -> List[ChatMessageData]
    - Embeddings: embedding:{chunk_id} -> EmbeddingChunk
    - Indexed files: index:{file_path_hash} -> IndexedFile
    
    Example usage:
        db = RedisDatabase()
        db.connect()
        
        # Write minion info
        db.write("minion:123", minion_info.to_dict())
        
        # Read minion info
        data = db.read("minion:123")
        minion = MinionInfo.from_dict(data)
        
        # Add to list
        db.list_push("minion:123:summaries", "First summary")
        
        db.disconnect()
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """
        Initialize RedisDatabase.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Optional password for authentication
            decode_responses: Whether to decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self._client is not None
    
    def connect(self) -> bool:
        """
        Connect to the Redis database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            return True
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
        except RedisError as e:
            logger.error(f"Redis error during connection: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the Redis database."""
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False
            logger.info("Disconnected from Redis")
    
    def _ensure_connected(self) -> None:
        """Ensure we're connected to Redis."""
        if not self.is_connected:
            raise ConnectionError("Not connected to Redis. Call connect() first.")
    
    def _serialize(self, value: Any) -> str:
        """Serialize a value for storage."""
        if isinstance(value, str):
            return value
        return json.dumps(value)
    
    def _deserialize(self, value: Optional[str]) -> Optional[Any]:
        """Deserialize a value from storage."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def write(self, key: str, value: Any) -> bool:
        """
        Write a value to the database.
        
        Args:
            key: The key to write to
            value: The value to write (will be JSON serialized if not string)
            
        Returns:
            True if write successful, False otherwise
        """
        self._ensure_connected()
        try:
            serialized = self._serialize(value)
            self._client.set(key, serialized)
            logger.debug(f"Wrote key: {key}")
            return True
        except RedisError as e:
            logger.error(f"Failed to write key {key}: {e}")
            return False
    
    def read(self, key: str) -> Optional[Any]:
        """
        Read a value from the database.
        
        Args:
            key: The key to read
            
        Returns:
            The deserialized value, or None if key doesn't exist
        """
        self._ensure_connected()
        try:
            value = self._client.get(key)
            return self._deserialize(value)
        except RedisError as e:
            logger.error(f"Failed to read key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the database.
        
        Args:
            key: The key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        self._ensure_connected()
        try:
            result = self._client.delete(key)
            logger.debug(f"Deleted key: {key} (result: {result})")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the database.
        
        Args:
            key: The key to check
            
        Returns:
            True if key exists, False otherwise
        """
        self._ensure_connected()
        try:
            return self._client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "minion:*")
            
        Returns:
            List of matching keys
        """
        self._ensure_connected()
        try:
            return self._client.keys(pattern)
        except RedisError as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []
    
    def flush(self) -> bool:
        """
        Flush all data from the current database.
        
        WARNING: This deletes all data!
        
        Returns:
            True if flush successful, False otherwise
        """
        self._ensure_connected()
        try:
            self._client.flushdb()
            logger.warning("Flushed Redis database")
            return True
        except RedisError as e:
            logger.error(f"Failed to flush database: {e}")
            return False
    
    # List operations for summaries and messages
    
    def list_push(self, key: str, value: Any) -> bool:
        """
        Push a value to a list (right side).
        
        Args:
            key: The list key
            value: The value to push
            
        Returns:
            True if push successful, False otherwise
        """
        self._ensure_connected()
        try:
            serialized = self._serialize(value)
            self._client.rpush(key, serialized)
            logger.debug(f"Pushed to list: {key}")
            return True
        except RedisError as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return False
    
    def list_get(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get values from a list.
        
        Args:
            key: The list key
            start: Start index (0-based)
            end: End index (-1 for all)
            
        Returns:
            List of deserialized values
        """
        self._ensure_connected()
        try:
            values = self._client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]
        except RedisError as e:
            logger.error(f"Failed to get list {key}: {e}")
            return []
    
    def list_length(self, key: str) -> int:
        """
        Get the length of a list.
        
        Args:
            key: The list key
            
        Returns:
            Length of the list
        """
        self._ensure_connected()
        try:
            return self._client.llen(key)
        except RedisError as e:
            logger.error(f"Failed to get list length {key}: {e}")
            return 0
    
    def list_clear(self, key: str) -> bool:
        """
        Clear all values from a list.
        
        Args:
            key: The list key
            
        Returns:
            True if clear successful, False otherwise
        """
        return self.delete(key)
    
    # High-level minion operations
    
    def save_minion_info(self, info: MinionInfo) -> bool:
        """
        Save minion info to the database.
        
        Args:
            info: MinionInfo to save
            
        Returns:
            True if save successful, False otherwise
        """
        key = f"minion:{info.minion_id}"
        return self.write(key, info.to_dict())
    
    def get_minion_info(self, minion_id: str) -> Optional[MinionInfo]:
        """
        Get minion info from the database.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            MinionInfo if found, None otherwise
        """
        key = f"minion:{minion_id}"
        data = self.read(key)
        if data:
            return MinionInfo.from_dict(data)
        return None
    
    def save_voice_data(self, minion_id: str, voice: VoiceData) -> bool:
        """
        Save voice data for a minion.
        
        Args:
            minion_id: The minion ID
            voice: VoiceData to save
            
        Returns:
            True if save successful, False otherwise
        """
        key = f"minion:{minion_id}:voice"
        return self.write(key, voice.to_dict())
    
    def get_voice_data(self, minion_id: str) -> Optional[VoiceData]:
        """
        Get voice data for a minion.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            VoiceData if found, None otherwise
        """
        key = f"minion:{minion_id}:voice"
        data = self.read(key)
        if data:
            return VoiceData.from_dict(data)
        return None
    
    def add_summary(self, minion_id: str, summary: str) -> bool:
        """
        Add a summary to a minion's summary list.
        
        Args:
            minion_id: The minion ID
            summary: The summary text
            
        Returns:
            True if add successful, False otherwise
        """
        key = f"minion:{minion_id}:summaries"
        return self.list_push(key, summary)
    
    def get_summaries(self, minion_id: str) -> List[str]:
        """
        Get all summaries for a minion.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            List of summary strings
        """
        key = f"minion:{minion_id}:summaries"
        return self.list_get(key)
    
    def clear_summaries(self, minion_id: str) -> bool:
        """
        Clear all summaries for a minion.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            True if clear successful, False otherwise
        """
        key = f"minion:{minion_id}:summaries"
        return self.list_clear(key)
    
    def add_chat_message(self, chat_uid: str, message: ChatMessageData) -> bool:
        """
        Add a chat message to a chat's message list.
        
        Args:
            chat_uid: The chat UID
            message: The ChatMessageData to add
            
        Returns:
            True if add successful, False otherwise
        """
        key = f"chat:{chat_uid}:messages"
        return self.list_push(key, message.to_dict())
    
    def get_chat_messages(self, chat_uid: str) -> List[ChatMessageData]:
        """
        Get all messages for a chat.
        
        Args:
            chat_uid: The chat UID
            
        Returns:
            List of ChatMessageData
        """
        key = f"chat:{chat_uid}:messages"
        data_list = self.list_get(key)
        return [ChatMessageData.from_dict(d) for d in data_list]
    
    def get_all_minion_ids(self) -> List[str]:
        """
        Get all minion IDs in the database.
        
        Returns:
            List of minion IDs
        """
        keys = self.keys("minion:*")
        # Extract minion IDs from keys like "minion:123"
        minion_ids = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 2:
                minion_ids.add(parts[1])
        return list(minion_ids)
    
    def get_all_chat_uids(self) -> List[str]:
        """
        Get all chat UIDs in the database.
        
        Returns:
            List of chat UIDs
        """
        keys = self.keys("chat:*:messages")
        # Extract chat UIDs from keys like "chat:abc:messages"
        chat_uids = []
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 2:
                chat_uids.append(parts[1])
        return chat_uids
