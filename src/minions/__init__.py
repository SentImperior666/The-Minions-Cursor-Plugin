"""
Minions package - Core components for the Cursor chat monitoring agent.

Components:
- Minion: Main orchestration class
- MinionAgent: LLM agent for summarization
- MinionVoice: Voice synthesis via ElevenLabs
- MinionMemory: State persistence via Redis
- CursorListener: Monitors Cursor chats for updates
- CursorDatabase: Reads Cursor's local SQLite database
- RedisDatabase: Local Redis database interface
- CodebaseIndexer: Indexes codebase for Q&A
"""

from .core import Minion, MinionState, MinionManager
from .cursor import CursorListener, CursorDatabase, CursorChat, ChatMessage
from .database import RedisDatabase
from .agent import MinionAgent
from .voice import MinionVoice
from .memory import MinionMemory

__all__ = [
    "Minion",
    "MinionState", 
    "MinionManager",
    "MinionAgent",
    "MinionVoice",
    "MinionMemory",
    "CursorListener",
    "CursorDatabase",
    "CursorChat",
    "ChatMessage",
    "RedisDatabase",
]
