"""
Core Minion classes - Main orchestration layer.

This module integrates all components:
- CursorListener/CursorDatabase from Task 1
- MinionAgent/MinionVoice/MinionMemory from Task 2
- RedisDatabase/CodebaseIndexer from Task 3
"""

import logging
import random
import string
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .cursor import CursorListener, CursorDatabase, CursorChat, ChatMessage
from .database import RedisDatabase
from .agent import MinionAgent
from .voice import MinionVoice
from .memory import MinionMemory
from .api import TwilioAPI, CallInfo

logger = logging.getLogger(__name__)

# Fun minion names (Despicable Me inspired)
MINION_NAMES = [
    "Bob", "Kevin", "Stuart", "Dave", "Jerry", "Tim", "Mark",
    "Phil", "Carl", "Tom", "Jorge", "Ken", "Lance", "Mike", "Norbert",
]


@dataclass
class MinionState:
    """Current state of a minion."""
    minion_id: str
    chat_uid: str
    name: str
    is_active: bool
    has_voice: bool
    summary_count: int
    created_at: datetime


class Minion:
    """
    Main Minion class that orchestrates all components.
    
    A Minion monitors a Cursor chat, summarizes conversations,
    and can call the user to report updates.
    
    Usage:
        # Spawn a new minion for a chat
        minion = Minion.spawn(chat_uid="abc123")
        
        # Get the current summary
        summary = minion.get_summary()
        
        # Call the user
        minion.call_user("+1234567890", webhook_url)
    """
    
    def __init__(
        self,
        minion_id: str,
        chat_uid: str,
        name: Optional[str] = None,
        agent: Optional[MinionAgent] = None,
        voice: Optional[MinionVoice] = None,
        memory: Optional[MinionMemory] = None,
        twilio: Optional[TwilioAPI] = None,
        redis_db: Optional[RedisDatabase] = None,
    ):
        """
        Initialize a Minion.
        
        Args:
            minion_id: Unique identifier.
            chat_uid: UID of the chat to monitor.
            name: Friendly name.
            agent: MinionAgent instance.
            voice: MinionVoice instance.
            memory: MinionMemory instance.
            twilio: TwilioAPI instance.
            redis_db: RedisDatabase instance.
        """
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self.name = name or self.create_name()
        self.agent = agent
        self.voice = voice
        self.memory = memory
        self._twilio = twilio or TwilioAPI()
        self._redis_db = redis_db or RedisDatabase()
        self._active_call: Optional[CallInfo] = None
        self._is_active = True
        self._created_at = datetime.now()
    
    @classmethod
    def spawn(
        cls,
        chat_uid: str,
        minion_id: Optional[str] = None,
        persist: bool = True,
        redis_db: Optional[RedisDatabase] = None,
    ) -> 'Minion':
        """
        Spawn a new or existing Minion.
        
        If minion_id is provided and exists, loads that minion.
        Otherwise creates a new minion.
        
        Args:
            chat_uid: UID of the Cursor chat to monitor.
            minion_id: Optional ID. If exists, loads; otherwise creates new.
            persist: Whether to persist the minion to storage.
            redis_db: Optional RedisDatabase instance.
            
        Returns:
            Spawned Minion instance.
        """
        # Generate ID if not provided
        if minion_id is None:
            minion_id = cls._generate_id()
        
        # Connect to Redis
        redis = redis_db or RedisDatabase()
        if not redis.is_connected:
            redis.connect()
        
        # Check if minion exists
        memory = MinionMemory(minion_id, chat_uid, redis)
        
        if memory.exists():
            logger.info("Loading existing minion: %s", minion_id)
            return cls.load(minion_id, chat_uid, redis_db=redis)
        else:
            logger.info("Creating new minion: %s", minion_id)
            return cls.create(minion_id, chat_uid, redis_db=redis)
    
    @classmethod
    def create(
        cls,
        minion_id: str,
        chat_uid: str,
        redis_db: Optional[RedisDatabase] = None,
    ) -> 'Minion':
        """
        Create a new Minion with fresh components.
        
        Args:
            minion_id: Unique identifier for the minion.
            chat_uid: UID of the Cursor chat to monitor.
            redis_db: Optional RedisDatabase instance.
            
        Returns:
            Created Minion instance.
        """
        logger.info("Creating minion %s for chat %s", minion_id, chat_uid)
        
        redis = redis_db or RedisDatabase()
        if not redis.is_connected:
            redis.connect()
        
        # Create the minion name
        name = cls.create_name()
        
        # Initialize memory
        memory = MinionMemory.init(minion_id, chat_uid, redis)
        memory.save_name(name)
        
        # Initialize voice with the name
        voice = MinionVoice.init(minion_id, name)
        memory.save_voice(voice)
        
        # Initialize agent and summarize existing chat
        agent = MinionAgent.init(minion_id, chat_uid, redis)
        
        # Save initial summary if available
        if agent.get_current_summary():
            memory.save_summary(agent.get_current_summary())
        
        minion = cls(
            minion_id=minion_id,
            chat_uid=chat_uid,
            name=name,
            agent=agent,
            voice=voice,
            memory=memory,
            redis_db=redis,
        )
        
        logger.info("Minion %s (%s) created successfully", minion_id, name)
        return minion
    
    @classmethod
    def load(
        cls,
        minion_id: str,
        chat_uid: str,
        redis_db: Optional[RedisDatabase] = None,
    ) -> 'Minion':
        """
        Load an existing Minion from storage.
        
        Args:
            minion_id: ID of the minion to load.
            chat_uid: UID of the Cursor chat.
            redis_db: Optional RedisDatabase instance.
            
        Returns:
            Loaded Minion instance.
        """
        logger.info("Loading minion %s for chat %s", minion_id, chat_uid)
        
        redis = redis_db or RedisDatabase()
        if not redis.is_connected:
            redis.connect()
        
        # Initialize memory
        memory = MinionMemory.init(minion_id, chat_uid, redis)
        
        # Get minion info
        info = memory.get_info()
        name = info.minion_name if info else cls.create_name()
        
        # Load voice from stored data
        voice_info = memory.get_voice_info()
        if voice_info and voice_info.get("voice_id"):
            voice = MinionVoice.load(minion_id, voice_info)
        else:
            voice = MinionVoice.init(minion_id, name)
            memory.save_voice(voice)
        
        # Initialize agent and summarize chat
        agent = MinionAgent.init(minion_id, chat_uid, redis)
        
        # Save new summary
        if agent.get_current_summary():
            memory.save_summary(agent.get_current_summary())
        
        minion = cls(
            minion_id=minion_id,
            chat_uid=chat_uid,
            name=name,
            agent=agent,
            voice=voice,
            memory=memory,
            redis_db=redis,
        )
        
        logger.info("Minion %s (%s) loaded successfully", minion_id, name)
        return minion
    
    @staticmethod
    def _generate_id() -> str:
        """Generate a unique minion ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"minion_{timestamp}_{random_suffix}"
    
    @staticmethod
    def create_name() -> str:
        """Create a unique minion name."""
        base = random.choice(MINION_NAMES)
        suffix = random.randint(1, 99)
        return f"{base}-{suffix}"
    
    def call_user(
        self,
        phone_number: str,
        webhook_url: str,
        message: Optional[str] = None,
    ) -> CallInfo:
        """
        Initiate a phone call to the user.
        
        Args:
            phone_number: User's phone number (E.164 format).
            webhook_url: URL for TwiML instructions.
            message: Optional message to speak.
            
        Returns:
            CallInfo with call details.
        """
        logger.info("Minion %s initiating call to %s", self.name, phone_number)
        
        call = self._twilio.initiate_call(
            to_number=phone_number,
            webhook_url=webhook_url,
        )
        
        self._active_call = call
        return call
    
    def speak(self, text: str) -> bytes:
        """Convert text to speech using the minion's voice."""
        if not self.voice:
            logger.warning("No voice configured for minion %s", self.minion_id)
            return b""
        return self.voice.text_to_speech(text)
    
    def get_summary(self) -> str:
        """Get the current chat summary."""
        if self.agent:
            return self.agent.get_current_summary() or "No summary available."
        return "Agent not initialized."
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """Process a voice command from the user."""
        if not self.agent:
            return {"error": "Agent not initialized", "success": False}
        
        result = self.agent.process_command(command)
        
        # Handle special actions
        if result.action == "stop":
            self._is_active = False
        elif result.action == "forget" and self.memory:
            self.memory._clear_summaries()
        elif result.action == "spawn":
            new_id = result.parameters.get("new_minion_id")
            if new_id:
                Minion.spawn(self.chat_uid, new_id, redis_db=self._redis_db)
        
        return {
            "action": result.action,
            "response": result.response,
            "success": result.success,
        }
    
    def get_state(self) -> MinionState:
        """Get the current state of the minion."""
        summary_count = 0
        if self.memory:
            summary_count = len(self.memory.get_summaries())
        
        return MinionState(
            minion_id=self.minion_id,
            chat_uid=self.chat_uid,
            name=self.name,
            is_active=self._is_active,
            has_voice=self.voice is not None and self.voice.voice_id is not None,
            summary_count=summary_count,
            created_at=self._created_at,
        )
    
    def stop(self) -> None:
        """Stop the minion."""
        self._is_active = False
        logger.info("Minion %s stopped", self.minion_id)
    
    def is_active(self) -> bool:
        """Check if the minion is active."""
        return self._is_active
    
    def __repr__(self) -> str:
        return f"Minion(id={self.minion_id}, name={self.name}, chat={self.chat_uid})"


class MinionManager:
    """
    Manages multiple Minions and coordinates with CursorListener.
    
    This is the main entry point for the application.
    
    Usage:
        manager = MinionManager()
        manager.start()  # Starts monitoring all Cursor chats
    """
    
    def __init__(
        self,
        cursor_db: Optional[CursorDatabase] = None,
        redis_db: Optional[RedisDatabase] = None,
        auto_spawn: bool = True,
        poll_interval: float = 2.0,
    ):
        """
        Initialize the MinionManager.
        
        Args:
            cursor_db: CursorDatabase instance.
            redis_db: RedisDatabase instance.
            auto_spawn: Whether to auto-spawn minions for new chats.
            poll_interval: Seconds between database polls.
        """
        self._redis_db = redis_db or RedisDatabase()
        self._cursor_db = cursor_db
        self._listener: Optional[CursorListener] = None
        self._minions: Dict[str, Minion] = {}
        self._auto_spawn = auto_spawn
        self._poll_interval = poll_interval
        self._running = False
        
        # Callbacks
        self._on_new_message: Optional[Callable[[ChatMessage], None]] = None
        self._on_minion_created: Optional[Callable[[Minion], None]] = None
    
    def start(self, blocking: bool = True) -> None:
        """
        Start monitoring Cursor chats.
        
        Args:
            blocking: If True, blocks the current thread.
        """
        logger.info("Starting MinionManager...")
        
        # Connect to Redis
        if not self._redis_db.is_connected:
            if not self._redis_db.connect():
                logger.error("Failed to connect to Redis. Using in-memory fallback.")
        
        # Initialize CursorListener
        self._listener = CursorListener(
            cursor_db=self._cursor_db,
            redis_db=self._redis_db,
            poll_interval=self._poll_interval,
        )
        
        # Set up callbacks
        self._listener.set_global_callbacks(
            on_any_message=self._handle_new_message,
            on_any_update=self._handle_chat_update,
        )
        
        # Scan for existing chats
        chat_uids = self._listener.scan()
        logger.info("Found %d active chats", len(chat_uids))
        
        # Register all chats and optionally spawn minions
        for uid in chat_uids:
            self._listener.register(uid)
            if self._auto_spawn and uid not in self._minions:
                self._spawn_minion_for_chat(uid)
        
        self._running = True
        
        # Start the listener
        self._listener.start(blocking=blocking)
    
    def stop(self) -> None:
        """Stop the manager and all minions."""
        logger.info("Stopping MinionManager...")
        self._running = False
        
        if self._listener:
            self._listener.stop()
        
        for minion in self._minions.values():
            minion.stop()
        
        if self._redis_db.is_connected:
            self._redis_db.disconnect()
    
    def _spawn_minion_for_chat(self, chat_uid: str) -> Optional[Minion]:
        """Spawn a minion for a chat."""
        try:
            minion = Minion.spawn(chat_uid, redis_db=self._redis_db)
            self._minions[chat_uid] = minion
            
            if self._on_minion_created:
                self._on_minion_created(minion)
            
            return minion
        except Exception as e:
            logger.error("Failed to spawn minion for chat %s: %s", chat_uid, e)
            return None
    
    def _handle_new_message(self, message: ChatMessage) -> None:
        """Handle a new message from any chat."""
        logger.debug("New message in chat %s: %s", message.chat_uid, message)
        
        # Get or create minion for this chat
        if message.chat_uid not in self._minions and self._auto_spawn:
            self._spawn_minion_for_chat(message.chat_uid)
        
        minion = self._minions.get(message.chat_uid)
        if minion and minion.agent:
            # Update the agent with new message
            minion.agent.process_new_message(message)
        
        if self._on_new_message:
            self._on_new_message(message)
    
    def _handle_chat_update(self, chat: CursorChat) -> None:
        """Handle a chat update."""
        logger.debug("Chat updated: %s (%d messages)", chat.uid, chat.message_count)
    
    def get_minion(self, chat_uid: str) -> Optional[Minion]:
        """Get the minion for a specific chat."""
        return self._minions.get(chat_uid)
    
    def get_all_minions(self) -> List[Minion]:
        """Get all active minions."""
        return list(self._minions.values())
    
    def set_callbacks(
        self,
        on_new_message: Optional[Callable[[ChatMessage], None]] = None,
        on_minion_created: Optional[Callable[[Minion], None]] = None,
    ) -> None:
        """Set callback functions."""
        self._on_new_message = on_new_message
        self._on_minion_created = on_minion_created
    
    @property
    def is_running(self) -> bool:
        """Check if the manager is running."""
        return self._running
