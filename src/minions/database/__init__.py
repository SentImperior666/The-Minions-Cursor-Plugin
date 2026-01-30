"""
Database module - Redis database interface.

Wraps implementation from xfw workspace (Task 3 - Xavier).
"""

from .redis_database import RedisDatabase, RedisDatabaseInterface
from .data_types import (
    MinionInfo,
    VoiceData,
    ChatMessageData,
    SearchResult,
    IndexedFile,
    EmbeddingChunk,
)

__all__ = [
    "RedisDatabase",
    "RedisDatabaseInterface",
    "MinionInfo",
    "VoiceData",
    "ChatMessageData",
    "SearchResult",
    "IndexedFile",
    "EmbeddingChunk",
]
