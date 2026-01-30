"""
Data models for Cursor chat integration.

These types represent chat data read from Cursor's local database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class ChatMessage:
    """
    Represents a single message in a Cursor chat.
    """
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    chat_uid: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.role not in ('user', 'assistant'):
            raise ValueError(f"Invalid role: {self.role}. Must be 'user' or 'assistant'")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'chat_uid': self.chat_uid,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            id=data['id'],
            role=data['role'],
            content=data['content'],
            timestamp=timestamp,
            chat_uid=data['chat_uid'],
            metadata=data.get('metadata', {}),
        )
    
    @classmethod
    def from_cursor_row(cls, row: Dict[str, Any], chat_uid: str) -> 'ChatMessage':
        timestamp_raw = row.get('timestamp', row.get('createdAt', 0))
        if isinstance(timestamp_raw, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp_raw / 1000)
        else:
            timestamp = datetime.fromisoformat(str(timestamp_raw))
        
        content = row.get('content', row.get('text', row.get('message', '')))
        if isinstance(content, dict):
            content = content.get('text', json.dumps(content))
        
        return cls(
            id=str(row.get('id', row.get('messageId', ''))),
            role=row.get('role', row.get('type', 'user')),
            content=str(content),
            timestamp=timestamp,
            chat_uid=chat_uid,
            metadata={k: v for k, v in row.items() 
                     if k not in ('id', 'role', 'content', 'timestamp', 'text', 'message', 'createdAt', 'messageId', 'type')},
        )
    
    def __str__(self) -> str:
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"[{self.role}] {content_preview}"


@dataclass
class CursorChat:
    """
    Represents a complete chat session from Cursor.
    """
    uid: str
    messages: List[ChatMessage] = field(default_factory=list)
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    workspace_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'uid': self.uid,
            'title': self.title,
            'messages': [msg.to_dict() for msg in self.messages],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'workspace_path': self.workspace_path,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CursorChat':
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        messages = [
            ChatMessage.from_dict(msg) if isinstance(msg, dict) else msg
            for msg in data.get('messages', [])
        ]
        
        return cls(
            uid=data['uid'],
            title=data.get('title'),
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            workspace_path=data.get('workspace_path'),
            metadata=data.get('metadata', {}),
        )
    
    def get_latest_message(self) -> Optional[ChatMessage]:
        if not self.messages:
            return None
        return max(self.messages, key=lambda m: m.timestamp)
    
    def get_messages_since(self, timestamp: datetime) -> List[ChatMessage]:
        return [msg for msg in self.messages if msg.timestamp > timestamp]
    
    def get_user_messages(self) -> List[ChatMessage]:
        return [msg for msg in self.messages if msg.role == 'user']
    
    def get_assistant_messages(self) -> List[ChatMessage]:
        return [msg for msg in self.messages if msg.role == 'assistant']
    
    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def is_empty(self) -> bool:
        return len(self.messages) == 0
    
    def __str__(self) -> str:
        title = self.title or f"Chat {self.uid[:8]}"
        return f"{title} ({self.message_count} messages)"
    
    def __len__(self) -> int:
        return len(self.messages)
