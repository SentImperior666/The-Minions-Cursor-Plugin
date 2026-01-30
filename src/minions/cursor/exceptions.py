"""
Custom exceptions for Cursor integration.
"""

from typing import List, Optional


class CursorDatabaseError(Exception):
    """Base exception for Cursor database errors."""
    pass


class CursorDatabaseNotFoundError(CursorDatabaseError):
    """Raised when Cursor database file cannot be found."""
    
    def __init__(self, searched_paths: Optional[List[str]] = None):
        self.searched_paths = searched_paths or []
        paths_str = ", ".join(self.searched_paths) if self.searched_paths else "unknown"
        super().__init__(f"Cursor database not found. Searched: {paths_str}")


class CursorDatabaseLockedError(CursorDatabaseError):
    """Raised when Cursor database is locked (being written to)."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        super().__init__(f"Cursor database is locked: {db_path}")


class ChatNotFoundError(CursorDatabaseError):
    """Raised when a specific chat cannot be found."""
    
    def __init__(self, chat_uid: str):
        self.chat_uid = chat_uid
        super().__init__(f"Chat not found: {chat_uid}")
