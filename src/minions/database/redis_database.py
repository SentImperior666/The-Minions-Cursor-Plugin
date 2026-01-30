"""
Redis Database Interface for The Minions Cursor Plugin.

Provides both a real Redis implementation and an in-memory mock
for development without Redis server.
"""

import json
import logging
import fnmatch
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import redis, fall back to mock if not available
try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError, RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisConnectionError = Exception
    RedisError = Exception


class RedisDatabaseInterface(ABC):
    """Abstract interface for Redis database operations."""
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        pass
    
    @abstractmethod
    def write(self, key: str, value: Any) -> bool:
        pass
    
    @abstractmethod
    def read(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass


class InMemoryRedis(RedisDatabaseInterface):
    """In-memory Redis mock for development and testing."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._connected = False
    
    def connect(self) -> bool:
        self._connected = True
        logger.info("Connected to in-memory Redis mock")
        return True
    
    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from in-memory Redis mock")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def _serialize(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value)
    
    def _deserialize(self, value: Optional[str]) -> Optional[Any]:
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def write(self, key: str, value: Any) -> bool:
        with self._lock:
            self._data[key] = self._serialize(value)
            return True
    
    def read(self, key: str) -> Optional[Any]:
        with self._lock:
            value = self._data.get(key)
            return self._deserialize(value)
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._data
    
    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def list_push(self, key: str, value: Any) -> bool:
        with self._lock:
            existing = self._data.get(key)
            if existing is None:
                current_list = []
            else:
                current_list = self._deserialize(existing)
                if not isinstance(current_list, list):
                    current_list = [current_list]
            current_list.append(value)
            self._data[key] = self._serialize(current_list)
            return True
    
    def list_get(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        with self._lock:
            value = self._deserialize(self._data.get(key))
            if value is None:
                return []
            if not isinstance(value, list):
                return [value]
            if end == -1:
                return value[start:]
            return value[start:end + 1]
    
    def flush(self) -> bool:
        with self._lock:
            self._data.clear()
            return True


class RedisDatabase(RedisDatabaseInterface):
    """
    Redis database implementation.
    
    Falls back to in-memory storage if Redis is not available.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client = None
        self._connected = False
        self._use_mock = use_mock or not REDIS_AVAILABLE
        self._mock: Optional[InMemoryRedis] = None
        
        if self._use_mock:
            self._mock = InMemoryRedis()
    
    @property
    def is_connected(self) -> bool:
        if self._use_mock:
            return self._mock.is_connected if self._mock else False
        return self._connected and self._client is not None
    
    def connect(self) -> bool:
        if self._use_mock:
            return self._mock.connect() if self._mock else False
        
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            return True
        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._use_mock = True
            self._mock = InMemoryRedis()
            return self._mock.connect()
    
    def disconnect(self) -> None:
        if self._use_mock and self._mock:
            self._mock.disconnect()
            return
        
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False
            logger.info("Disconnected from Redis")
    
    def _serialize(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value)
    
    def _deserialize(self, value: Optional[str]) -> Optional[Any]:
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def write(self, key: str, value: Any) -> bool:
        if self._use_mock and self._mock:
            return self._mock.write(key, value)
        
        if not self.is_connected:
            return False
        
        try:
            serialized = self._serialize(value)
            self._client.set(key, serialized)
            return True
        except RedisError as e:
            logger.error(f"Failed to write key {key}: {e}")
            return False
    
    def read(self, key: str) -> Optional[Any]:
        if self._use_mock and self._mock:
            return self._mock.read(key)
        
        if not self.is_connected:
            return None
        
        try:
            value = self._client.get(key)
            return self._deserialize(value)
        except RedisError as e:
            logger.error(f"Failed to read key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        if self._use_mock and self._mock:
            return self._mock.delete(key)
        
        if not self.is_connected:
            return False
        
        try:
            return self._client.delete(key) > 0
        except RedisError as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        if self._use_mock and self._mock:
            return self._mock.exists(key)
        
        if not self.is_connected:
            return False
        
        try:
            return self._client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        if self._use_mock and self._mock:
            return self._mock.keys(pattern)
        
        if not self.is_connected:
            return []
        
        try:
            return self._client.keys(pattern)
        except RedisError as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []
    
    def list_push(self, key: str, value: Any) -> bool:
        if self._use_mock and self._mock:
            return self._mock.list_push(key, value)
        
        if not self.is_connected:
            return False
        
        try:
            serialized = self._serialize(value)
            self._client.rpush(key, serialized)
            return True
        except RedisError as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return False
    
    def list_get(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        if self._use_mock and self._mock:
            return self._mock.list_get(key, start, end)
        
        if not self.is_connected:
            return []
        
        try:
            values = self._client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]
        except RedisError as e:
            logger.error(f"Failed to get list {key}: {e}")
            return []
    
    def flush(self) -> bool:
        if self._use_mock and self._mock:
            return self._mock.flush()
        
        if not self.is_connected:
            return False
        
        try:
            self._client.flushdb()
            return True
        except RedisError as e:
            logger.error(f"Failed to flush database: {e}")
            return False
    
    def list_length(self, key: str) -> int:
        """
        Get the length of a list.
        
        Args:
            key: The list key
            
        Returns:
            Length of the list
        """
        if self._use_mock and self._mock:
            return len(self._mock.list_get(key))
        
        if not self.is_connected:
            return 0
        
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
    
    # Alias for Victor's MinionMemory which uses list_append
    def list_append(self, key: str, value: Any) -> bool:
        """Alias for list_push for compatibility."""
        return self.list_push(key, value)
    
    # High-level minion operations (from Xavier's implementation)
    
    def save_minion_info(self, info: 'MinionInfo') -> bool:
        """
        Save minion info to the database.
        
        Args:
            info: MinionInfo to save
            
        Returns:
            True if save successful, False otherwise
        """
        from .data_types import MinionInfo as MI
        key = f"minion:{info.minion_id}"
        return self.write(key, info.to_dict())
    
    def get_minion_info(self, minion_id: str) -> Optional['MinionInfo']:
        """
        Get minion info from the database.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            MinionInfo if found, None otherwise
        """
        from .data_types import MinionInfo
        key = f"minion:{minion_id}"
        data = self.read(key)
        if data:
            return MinionInfo.from_dict(data)
        return None
    
    def save_voice_data(self, minion_id: str, voice: 'VoiceData') -> bool:
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
    
    def get_voice_data(self, minion_id: str) -> Optional['VoiceData']:
        """
        Get voice data for a minion.
        
        Args:
            minion_id: The minion ID
            
        Returns:
            VoiceData if found, None otherwise
        """
        from .data_types import VoiceData
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
    
    def add_chat_message(self, chat_uid: str, message: 'ChatMessageData') -> bool:
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
    
    def get_chat_messages(self, chat_uid: str) -> List['ChatMessageData']:
        """
        Get all messages for a chat.
        
        Args:
            chat_uid: The chat UID
            
        Returns:
            List of ChatMessageData
        """
        from .data_types import ChatMessageData
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
