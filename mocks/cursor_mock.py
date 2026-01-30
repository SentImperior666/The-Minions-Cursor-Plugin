"""
Mock implementation of CursorChat and ChatMessage data types.

This is a placeholder for Marcus's Task 1 implementation.
The actual implementation will be in the uwm workspace.

These data types represent chat messages from the Cursor IDE database.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """
    Represents a single message in a Cursor chat.
    
    Attributes:
        role: Who sent the message (user, assistant, or system)
        content: The text content of the message
        timestamp: When the message was sent
        message_id: Optional unique identifier for the message
    """
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None
    
    def __post_init__(self):
        """Convert string role to MessageRole enum if needed."""
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)
    
    def to_dict(self) -> dict:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatMessage':
        """Create a ChatMessage from a dictionary."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            message_id=data.get("message_id"),
        )


@dataclass
class CursorChat:
    """
    Represents a complete chat session from Cursor.
    
    Attributes:
        chat_uid: Unique identifier for the chat
        messages: List of messages in the chat
        created_at: When the chat was created
        updated_at: When the chat was last updated
        workspace_path: Optional path to the workspace this chat belongs to
    """
    chat_uid: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    workspace_path: Optional[str] = None
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the chat and update timestamp."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_user_messages(self) -> List[ChatMessage]:
        """Get all user messages in the chat."""
        return [m for m in self.messages if m.role == MessageRole.USER]
    
    def get_assistant_messages(self) -> List[ChatMessage]:
        """Get all assistant messages in the chat."""
        return [m for m in self.messages if m.role == MessageRole.ASSISTANT]
    
    def get_messages_since(self, timestamp: datetime) -> List[ChatMessage]:
        """Get all messages since a given timestamp."""
        return [m for m in self.messages if m.timestamp > timestamp]
    
    def to_dict(self) -> dict:
        """Convert chat to dictionary for serialization."""
        return {
            "chat_uid": self.chat_uid,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "workspace_path": self.workspace_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CursorChat':
        """Create a CursorChat from a dictionary."""
        return cls(
            chat_uid=data["chat_uid"],
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            workspace_path=data.get("workspace_path"),
        )
    
    def get_conversation_text(self) -> str:
        """Get the full conversation as a formatted string."""
        lines = []
        for msg in self.messages:
            role_label = msg.role.value.upper()
            lines.append(f"[{role_label}]: {msg.content}")
        return "\n\n".join(lines)
    
    def __len__(self) -> int:
        """Return the number of messages in the chat."""
        return len(self.messages)
