"""
CursorDatabase - Interface to read Cursor's local SQLite database.
"""

import json
import os
import platform
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from .exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseLockedError,
)
from .models import ChatMessage, CursorChat


class CursorDatabase:
    """
    Reads Cursor's local SQLite database containing chat history.
    
    Cursor stores chats in a SQLite database, typically located at:
    - Windows: %APPDATA%/Cursor/User/globalStorage/state.vscdb
    - macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
    - Linux: ~/.config/Cursor/User/globalStorage/state.vscdb
    """
    
    CHAT_DATA_KEY_PREFIX = "workbench.panel.aichat.chatdata"
    CHAT_HISTORY_KEY = "workbench.panel.aichat.chatHistory"
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self._db_path = Path(db_path)
            if not self._db_path.exists():
                raise CursorDatabaseNotFoundError([str(self._db_path)])
        else:
            self._db_path = self._find_database()
    
    def _find_database(self) -> Path:
        system = platform.system()
        possible_paths: List[Path] = []
        
        if system == "Windows":
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                possible_paths.append(
                    Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
                )
            localappdata = os.environ.get("LOCALAPPDATA", "")
            if localappdata:
                possible_paths.append(
                    Path(localappdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
                )
        elif system == "Darwin":
            home = Path.home()
            possible_paths.append(
                home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
            )
        else:
            home = Path.home()
            possible_paths.append(
                home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
            )
        
        for path in possible_paths:
            if path.exists():
                return path
        
        raise CursorDatabaseNotFoundError([str(p) for p in possible_paths])
    
    @property
    def db_path(self) -> str:
        return str(self._db_path)
    
    def _connect(self) -> sqlite3.Connection:
        try:
            uri = f"file:{self._db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                raise CursorDatabaseLockedError(str(self._db_path))
            raise
    
    def _get_value(self, key: str) -> Optional[Any]:
        try:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "SELECT value FROM ItemTable WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
                return None
            finally:
                conn.close()
        except (sqlite3.Error, json.JSONDecodeError):
            return None
    
    def _get_all_chat_keys(self) -> List[str]:
        try:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "SELECT key FROM ItemTable WHERE key LIKE ?",
                    (f"{self.CHAT_DATA_KEY_PREFIX}%",)
                )
                return [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
        except sqlite3.Error:
            return []
    
    def get_active_chats(self) -> List[str]:
        chat_uids: List[str] = []
        
        history = self._get_value(self.CHAT_HISTORY_KEY)
        if history and isinstance(history, list):
            for item in history:
                if isinstance(item, dict) and 'id' in item:
                    chat_uids.append(item['id'])
                elif isinstance(item, str):
                    chat_uids.append(item)
        
        chat_keys = self._get_all_chat_keys()
        for key in chat_keys:
            parts = key.split('.')
            if len(parts) > 4:
                uid = '.'.join(parts[4:])
                if uid and uid not in chat_uids:
                    chat_uids.append(uid)
        
        return chat_uids
    
    def get_chat(self, chat_uid: str) -> Optional[CursorChat]:
        possible_keys = [
            f"{self.CHAT_DATA_KEY_PREFIX}.{chat_uid}",
            f"{self.CHAT_DATA_KEY_PREFIX}/{chat_uid}",
            chat_uid,
        ]
        
        chat_data = None
        for key in possible_keys:
            chat_data = self._get_value(key)
            if chat_data:
                break
        
        if not chat_data:
            return None
        
        return self._parse_chat_data(chat_uid, chat_data)
    
    def _parse_chat_data(self, chat_uid: str, data: Any) -> CursorChat:
        messages: List[ChatMessage] = []
        title: Optional[str] = None
        workspace_path: Optional[str] = None
        created_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None
        
        if isinstance(data, dict):
            title = data.get('title', data.get('name'))
            workspace_path = data.get('workspacePath', data.get('workspace'))
            
            if 'createdAt' in data:
                created_at = self._parse_timestamp(data['createdAt'])
            if 'updatedAt' in data:
                updated_at = self._parse_timestamp(data['updatedAt'])
            
            raw_messages = data.get('messages', data.get('conversation', []))
            if isinstance(raw_messages, list):
                for idx, msg in enumerate(raw_messages):
                    try:
                        if isinstance(msg, dict):
                            messages.append(
                                ChatMessage.from_cursor_row(msg, chat_uid)
                            )
                        elif isinstance(msg, str):
                            messages.append(ChatMessage(
                                id=f"{chat_uid}_{idx}",
                                role='user',
                                content=msg,
                                timestamp=datetime.now(),
                                chat_uid=chat_uid,
                            ))
                    except Exception:
                        continue
        
        return CursorChat(
            uid=chat_uid,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            workspace_path=workspace_path,
        )
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            if value > 1e12:
                value = value / 1000
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None
    
    def get_chat_messages(
        self,
        chat_uid: str,
        since: Optional[datetime] = None
    ) -> List[ChatMessage]:
        chat = self.get_chat(chat_uid)
        if not chat:
            return []
        
        if since:
            return chat.get_messages_since(since)
        return chat.messages
    
    def get_latest_message_timestamp(self, chat_uid: str) -> Optional[datetime]:
        chat = self.get_chat(chat_uid)
        if not chat:
            return None
        
        latest = chat.get_latest_message()
        if latest:
            return latest.timestamp
        return None
    
    def chat_exists(self, chat_uid: str) -> bool:
        return self.get_chat(chat_uid) is not None
    
    def get_all_chats(self) -> List[CursorChat]:
        chats: List[CursorChat] = []
        for uid in self.get_active_chats():
            chat = self.get_chat(uid)
            if chat:
                chats.append(chat)
        return chats
    
    def search_messages(self, query: str, case_sensitive: bool = False) -> List[ChatMessage]:
        results: List[ChatMessage] = []
        search_query = query if case_sensitive else query.lower()
        
        for chat in self.get_all_chats():
            for message in chat.messages:
                content = message.content if case_sensitive else message.content.lower()
                if search_query in content:
                    results.append(message)
        
        return results
