"""
Data types for The Minions Cursor Plugin.

These types are used by:
- RedisDatabase: For storing and retrieving minion data
- MinionMemory (Task 2): For persisting minion state
- CursorListener (Task 1): For storing chat messages
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Any
import json


@dataclass
class MinionInfo:
    """Information about a Minion instance."""
    minion_id: str
    chat_uid: str
    minion_name: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "minion_id": self.minion_id,
            "chat_uid": self.chat_uid,
            "minion_name": self.minion_name,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MinionInfo":
        """Create from dictionary."""
        return cls(
            minion_id=data["minion_id"],
            chat_uid=data["chat_uid"],
            minion_name=data["minion_name"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "MinionInfo":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class VoiceData:
    """Voice configuration for a Minion."""
    voice_name: str
    voice_description: str
    elevenlabs_voice_id: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "voice_name": self.voice_name,
            "voice_description": self.voice_description,
            "elevenlabs_voice_id": self.elevenlabs_voice_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VoiceData":
        """Create from dictionary."""
        return cls(
            voice_name=data["voice_name"],
            voice_description=data["voice_description"],
            elevenlabs_voice_id=data["elevenlabs_voice_id"]
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "VoiceData":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ChatMessageData:
    """
    A chat message from Cursor.
    
    This is the data type that CursorListener (Task 1) will use
    to store messages in Redis.
    """
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessageData":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_id=data.get("message_id")
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "ChatMessageData":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class SearchResult:
    """Result from CodebaseIndexer search."""
    file_path: str
    content: str
    score: float
    line_start: int
    line_end: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "content": self.content,
            "score": self.score,
            "line_start": self.line_start,
            "line_end": self.line_end
        }


@dataclass
class IndexedFile:
    """Metadata for an indexed file in CodebaseIndexer."""
    file_path: str
    content_hash: str
    chunk_ids: List[str] = field(default_factory=list)
    indexed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "chunk_ids": self.chunk_ids,
            "indexed_at": self.indexed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "IndexedFile":
        """Create from dictionary."""
        return cls(
            file_path=data["file_path"],
            content_hash=data["content_hash"],
            chunk_ids=data.get("chunk_ids", []),
            indexed_at=datetime.fromisoformat(data["indexed_at"])
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "IndexedFile":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class EmbeddingChunk:
    """A chunk of code with its embedding for semantic search."""
    chunk_id: str
    file_path: str
    content: str
    embedding: List[float]
    line_start: int
    line_end: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "file_path": self.file_path,
            "content": self.content,
            "embedding": self.embedding,
            "line_start": self.line_start,
            "line_end": self.line_end
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EmbeddingChunk":
        """Create from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            file_path=data["file_path"],
            content=data["content"],
            embedding=data["embedding"],
            line_start=data["line_start"],
            line_end=data["line_end"]
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "EmbeddingChunk":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
