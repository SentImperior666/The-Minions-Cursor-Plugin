"""
Cursor integration module.

Provides components for reading and monitoring Cursor's chat database.
Wraps implementations from uwm workspace (Task 1 - Marcus).
"""

# Re-export from uwm implementation
# In production, these would be properly packaged
# For now, we provide compatible interfaces

from .database import CursorDatabase
from .listener import CursorListener
from .models import CursorChat, ChatMessage
from .exceptions import (
    CursorDatabaseError,
    CursorDatabaseNotFoundError,
    CursorDatabaseLockedError,
    ChatNotFoundError,
)

__all__ = [
    "CursorDatabase",
    "CursorListener",
    "CursorChat",
    "ChatMessage",
    "CursorDatabaseError",
    "CursorDatabaseNotFoundError",
    "CursorDatabaseLockedError",
    "ChatNotFoundError",
]
