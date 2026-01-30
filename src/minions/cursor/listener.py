"""
CursorListener - Monitors Cursor chats for updates.
"""

import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .database import CursorDatabase
from .models import ChatMessage, CursorChat


MessageCallback = Callable[[ChatMessage], None]
ChatCallback = Callable[[CursorChat], None]


class ChatRegistration:
    """Holds registration data for a monitored chat."""
    
    def __init__(
        self,
        chat_uid: str,
        on_new_message: Optional[MessageCallback] = None,
        on_chat_update: Optional[ChatCallback] = None,
    ):
        self.chat_uid = chat_uid
        self.on_new_message = on_new_message
        self.on_chat_update = on_chat_update
        self.last_message_timestamp: Optional[datetime] = None
        self.last_message_count: int = 0


class CursorListener:
    """
    Monitors Cursor chats for new messages and triggers callbacks.
    """
    
    def __init__(
        self,
        cursor_db: Optional[CursorDatabase] = None,
        redis_db: Optional[Any] = None,  # RedisDatabase interface
        poll_interval: float = 2.0,
    ):
        self._cursor_db = cursor_db
        self._redis_db = redis_db
        self._poll_interval = poll_interval
        
        self._registrations: Dict[str, ChatRegistration] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._on_any_message: Optional[MessageCallback] = None
        self._on_any_update: Optional[ChatCallback] = None
    
    @property
    def cursor_db(self) -> CursorDatabase:
        if self._cursor_db is None:
            self._cursor_db = CursorDatabase()
        return self._cursor_db
    
    @property
    def redis_db(self) -> Any:
        return self._redis_db
    
    def scan(self) -> List[str]:
        chat_uids = self.cursor_db.get_active_chats()
        
        if self._redis_db:
            self._redis_db.write("chats:active", chat_uids)
            for uid in chat_uids:
                chat = self.cursor_db.get_chat(uid)
                if chat:
                    self._sync_to_redis(chat)
        
        return chat_uids
    
    def register(
        self,
        chat_uid: str,
        on_new_message: Optional[MessageCallback] = None,
        on_chat_update: Optional[ChatCallback] = None,
    ) -> bool:
        if not self.cursor_db.chat_exists(chat_uid):
            return False
        
        with self._lock:
            registration = ChatRegistration(
                chat_uid=chat_uid,
                on_new_message=on_new_message,
                on_chat_update=on_chat_update,
            )
            
            chat = self.cursor_db.get_chat(chat_uid)
            if chat:
                registration.last_message_count = chat.message_count
                latest = chat.get_latest_message()
                if latest:
                    registration.last_message_timestamp = latest.timestamp
            
            self._registrations[chat_uid] = registration
        
        return True
    
    def unregister(self, chat_uid: str) -> bool:
        with self._lock:
            if chat_uid in self._registrations:
                del self._registrations[chat_uid]
                return True
            return False
    
    def set_global_callbacks(
        self,
        on_any_message: Optional[MessageCallback] = None,
        on_any_update: Optional[ChatCallback] = None,
    ) -> None:
        self._on_any_message = on_any_message
        self._on_any_update = on_any_update
    
    def start(self, blocking: bool = True) -> None:
        if self._running:
            return
        
        self._running = True
        
        if blocking:
            self._poll_loop()
        else:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
    
    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._poll_interval * 2)
    
    def get_registered_chats(self) -> List[str]:
        with self._lock:
            return list(self._registrations.keys())
    
    def is_running(self) -> bool:
        return self._running
    
    def _poll_loop(self) -> None:
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                print(f"Poll error: {e}")
            
            time.sleep(self._poll_interval)
    
    def _poll_once(self) -> None:
        with self._lock:
            registrations = list(self._registrations.values())
        
        for reg in registrations:
            try:
                self._check_chat_updates(reg)
            except Exception:
                continue
    
    def _check_chat_updates(self, reg: ChatRegistration) -> None:
        chat = self.cursor_db.get_chat(reg.chat_uid)
        if not chat:
            return
        
        new_messages: List[ChatMessage] = []
        
        if chat.message_count > reg.last_message_count:
            if reg.last_message_timestamp:
                new_messages = chat.get_messages_since(reg.last_message_timestamp)
            else:
                new_messages = chat.messages[reg.last_message_count:]
        
        if new_messages:
            with self._lock:
                if reg.chat_uid in self._registrations:
                    self._registrations[reg.chat_uid].last_message_count = chat.message_count
                    latest = chat.get_latest_message()
                    if latest:
                        self._registrations[reg.chat_uid].last_message_timestamp = latest.timestamp
            
            if self._redis_db:
                self._sync_to_redis(chat)
            
            for msg in new_messages:
                if reg.on_new_message:
                    try:
                        reg.on_new_message(msg)
                    except Exception:
                        pass
                
                if self._on_any_message:
                    try:
                        self._on_any_message(msg)
                    except Exception:
                        pass
            
            if reg.on_chat_update:
                try:
                    reg.on_chat_update(chat)
                except Exception:
                    pass
            
            if self._on_any_update:
                try:
                    self._on_any_update(chat)
                except Exception:
                    pass
    
    def _sync_to_redis(self, chat: CursorChat) -> None:
        if not self._redis_db:
            return
        
        uid = chat.uid
        
        metadata = {
            'uid': chat.uid,
            'title': chat.title,
            'created_at': chat.created_at.isoformat() if chat.created_at else None,
            'updated_at': chat.updated_at.isoformat() if chat.updated_at else None,
            'workspace_path': chat.workspace_path,
            'message_count': chat.message_count,
        }
        self._redis_db.write(f"chat:{uid}:metadata", metadata)
        
        messages = [msg.to_dict() for msg in chat.messages]
        self._redis_db.write(f"chat:{uid}:messages", messages)
    
    def poll_now(self) -> Dict[str, List[ChatMessage]]:
        results: Dict[str, List[ChatMessage]] = {}
        
        with self._lock:
            registrations = list(self._registrations.values())
        
        for reg in registrations:
            chat = self.cursor_db.get_chat(reg.chat_uid)
            if not chat:
                continue
            
            new_messages: List[ChatMessage] = []
            
            if chat.message_count > reg.last_message_count:
                if reg.last_message_timestamp:
                    new_messages = chat.get_messages_since(reg.last_message_timestamp)
                else:
                    new_messages = chat.messages[reg.last_message_count:]
            
            if new_messages:
                results[reg.chat_uid] = new_messages
                
                with self._lock:
                    if reg.chat_uid in self._registrations:
                        self._registrations[reg.chat_uid].last_message_count = chat.message_count
                        latest = chat.get_latest_message()
                        if latest:
                            self._registrations[reg.chat_uid].last_message_timestamp = latest.timestamp
                
                if self._redis_db:
                    self._sync_to_redis(chat)
        
        return results
