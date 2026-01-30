"""
Minion - Main orchestration class for the Minion agent.

Coordinates:
- MinionAgent for chat summarization
- MinionVoice for voice synthesis
- MinionMemory for state persistence
- Phone calls via Twilio
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import random
import string
import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.minions.agent import MinionAgent
from src.minions.voice import MinionVoice
from src.minions.memory import MinionMemory
from src.minions.api.twilio_api import TwilioAPI, CallInfo
from mocks.redis_mock import RedisDatabase

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
    
    Attributes:
        minion_id: Unique identifier for this minion
        chat_uid: UID of the Cursor chat being monitored
        name: Friendly name for the minion
        agent: MinionAgent for summarization
        voice: MinionVoice for speech synthesis
        memory: MinionMemory for persistence
        twilio: TwilioAPI for phone calls
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
        """
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self.name = name
        self.agent = agent
        self.voice = voice
        self.memory = memory
        self._twilio = twilio or TwilioAPI()
        self._active_call: Optional[CallInfo] = None
        self._is_active = True
    
    @classmethod
    def spawn(
        cls,
        chat_uid: str,
        minion_id: Optional[str] = None,
        persist: bool = True,
    ) -> 'Minion':
        """
        Spawn a new or existing Minion.
        
        If minion_id is provided and exists, loads that minion.
        Otherwise creates a new minion.
        
        Args:
            chat_uid: UID of the Cursor chat to monitor.
            minion_id: Optional ID. If exists, loads; otherwise creates new.
            persist: Whether to persist the minion to storage.
            
        Returns:
            Spawned Minion instance.
        """
        # Generate ID if not provided
        if minion_id is None:
            minion_id = cls._generate_id()
        
        # Check if minion exists
        redis = RedisDatabase()
        memory = MinionMemory(minion_id, chat_uid, redis)
        
        if memory.exists():
            logger.info("Loading existing minion: %s", minion_id)
            return cls.load(minion_id, chat_uid)
        else:
            logger.info("Creating new minion: %s", minion_id)
            return cls.create(minion_id, chat_uid)
    
    @classmethod
    def create(cls, minion_id: str, chat_uid: str) -> 'Minion':
        """
        Create a new Minion with fresh components.
        
        This:
        1. Creates a unique minion name
        2. Initializes MinionMemory
        3. Initializes MinionVoice with ElevenLabs
        4. Initializes MinionAgent
        5. Summarizes existing chat
        
        Args:
            minion_id: Unique identifier for the minion.
            chat_uid: UID of the Cursor chat to monitor.
            
        Returns:
            Created Minion instance.
        """
        logger.info("Creating minion %s for chat %s", minion_id, chat_uid)
        
        # Create the minion name
        name = cls.create_name()
        
        # Initialize memory
        memory = MinionMemory.init(minion_id, chat_uid)
        memory.save_name(name)
        
        # Initialize voice with the name
        voice = MinionVoice.init(minion_id, name)
        memory.save_voice(voice)
        
        # Initialize agent and summarize existing chat
        agent = MinionAgent.init(minion_id, chat_uid)
        
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
        )
        
        logger.info("Minion %s (%s) created successfully", minion_id, name)
        return minion
    
    @classmethod
    def load(cls, minion_id: str, chat_uid: str) -> 'Minion':
        """
        Load an existing Minion from storage.
        
        This:
        1. Loads minion info from MinionMemory
        2. Loads MinionVoice from stored data
        3. Initializes MinionAgent with new chat data
        4. Updates summary with any new messages
        
        Args:
            minion_id: ID of the minion to load.
            chat_uid: UID of the Cursor chat.
            
        Returns:
            Loaded Minion instance.
        """
        logger.info("Loading minion %s for chat %s", minion_id, chat_uid)
        
        # Initialize memory (clears summaries for fresh start)
        memory = MinionMemory.init(minion_id, chat_uid)
        
        # Get minion info
        info = memory.get_info()
        name = info.minion_name if info else cls.create_name()
        
        # Load voice from stored data
        voice_info = memory.get_voice_info()
        if voice_info and voice_info.get("voice_id"):
            voice = MinionVoice.load(minion_id, voice_info)
        else:
            # Create new voice if not found
            voice = MinionVoice.init(minion_id, name)
            memory.save_voice(voice)
        
        # Initialize agent and summarize chat
        agent = MinionAgent.init(minion_id, chat_uid)
        
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
        """
        Create a unique minion name.
        
        Returns:
            Generated name like "Bob-42" or "Kevin-17".
        """
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
            message: Optional message to speak. Uses summary if not provided.
            
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
        """
        Convert text to speech using the minion's voice.
        
        Args:
            text: Text to speak.
            
        Returns:
            Audio data as bytes.
        """
        if not self.voice:
            logger.warning("No voice configured for minion %s", self.minion_id)
            return b""
        
        return self.voice.text_to_speech(text)
    
    def get_summary(self) -> str:
        """
        Get the current chat summary.
        
        Returns:
            Summary string.
        """
        if self.agent:
            return self.agent.get_current_summary() or "No summary available."
        return "Agent not initialized."
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a voice command.
        
        Args:
            command: Voice command from user.
            
        Returns:
            Dict with action results.
        """
        if not self.agent:
            return {"error": "Agent not initialized", "success": False}
        
        result = self.agent.process_command(command)
        
        # Handle special actions
        if result.action == "stop":
            self._is_active = False
        elif result.action == "forget" and self.memory:
            # Clear memory via MinionMemory
            self.memory._clear_summaries()
        elif result.action == "spawn":
            # Create new minion
            new_id = result.parameters.get("new_minion_id")
            if new_id:
                Minion.spawn(self.chat_uid, new_id)
        
        return {
            "action": result.action,
            "response": result.response,
            "success": result.success,
        }
    
    def get_state(self) -> MinionState:
        """
        Get the current state of the minion.
        
        Returns:
            MinionState with current status.
        """
        summary_count = 0
        if self.memory:
            summary_count = len(self.memory.get_summaries())
        
        info = self.memory.get_info() if self.memory else None
        created_at = info.created_at if info else datetime.now()
        
        return MinionState(
            minion_id=self.minion_id,
            chat_uid=self.chat_uid,
            name=self.name or "Unnamed",
            is_active=self._is_active,
            has_voice=self.voice is not None and self.voice.voice_id is not None,
            summary_count=summary_count,
            created_at=created_at,
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
