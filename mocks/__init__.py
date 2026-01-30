"""
Mock implementations for dependencies from other tasks.

- redis_mock: Mock for RedisDatabase (Xavier's Task 3)
- cursor_mock: Mock for CursorChat/Database (Marcus's Task 1)
"""

from .redis_mock import RedisDatabase
from .cursor_mock import CursorChat, ChatMessage

__all__ = [
    "RedisDatabase",
    "CursorChat",
    "ChatMessage",
]
