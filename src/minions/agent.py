"""
MinionAgent - LLM agent for chat summarization and command processing.

Handles:
- Loading chat data from Cursor database
- Summarizing chat conversations
- Processing voice commands
- Calling MCP servers
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from mocks.cursor_mock import CursorChat, ChatMessage, MessageRole
from mocks.redis_mock import RedisDatabase
from src.minions.api.openai_api import OpenAIAPI

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of processing a voice command."""
    action: str
    parameters: Dict[str, Any]
    response: str
    success: bool = True


class MinionAgent:
    """
    LLM agent that summarizes Cursor chats and processes commands.
    
    The agent reads chat messages from the Cursor database (via mock),
    generates summaries using OpenAI, and processes voice commands.
    
    Attributes:
        minion_id: ID of the associated minion
        chat_uid: UID of the Cursor chat to monitor
        _openai: OpenAI API client
        _redis: Redis database for reading chat data
    """
    
    # Supported voice commands
    COMMANDS = {
        "stop": "Stop the current operation",
        "forget": "Clear memory and summaries",
        "spawn": "Create a new minion",
        "summarize": "Generate a summary",
        "status": "Get current status",
    }
    
    def __init__(
        self,
        minion_id: str,
        chat_uid: str,
        openai: Optional[OpenAIAPI] = None,
        redis: Optional[RedisDatabase] = None,
    ):
        """
        Initialize MinionAgent.
        
        Args:
            minion_id: ID of the associated minion.
            chat_uid: UID of the Cursor chat to monitor.
            openai: OpenAI API client.
            redis: Redis database instance.
        """
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self._openai = openai or OpenAIAPI()
        self._redis = redis or RedisDatabase()
        self._current_summary: Optional[str] = None
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        chat_uid: str,
        openai: Optional[OpenAIAPI] = None,
        redis: Optional[RedisDatabase] = None,
    ) -> 'MinionAgent':
        """
        Initialize a new MinionAgent and load the chat.
        
        Args:
            minion_id: ID of the associated minion.
            chat_uid: UID of the Cursor chat to monitor.
            openai: OpenAI API client.
            redis: Redis database instance.
            
        Returns:
            Initialized MinionAgent with chat loaded.
        """
        agent = cls(minion_id, chat_uid, openai, redis)
        
        # Load and summarize the initial chat
        chat = agent.load_chat(chat_uid)
        if chat and len(chat.messages) > 0:
            agent._current_summary = agent.summarize_chat(chat)
        
        return agent
    
    def load_chat(self, chat_uid: str) -> Optional[CursorChat]:
        """
        Load chat messages from the Redis database.
        
        In the actual implementation, this would read from the
        Cursor database via CursorListener. For now, it reads
        from Redis where CursorListener stores the messages.
        
        Args:
            chat_uid: UID of the chat to load.
            
        Returns:
            CursorChat with messages, or None if not found.
        """
        # Read chat data from Redis (stored by CursorListener)
        key = f"chat:{chat_uid}"
        data = self._redis.read(key)
        
        if not data:
            logger.info("No chat data found for %s, returning empty chat", chat_uid)
            return CursorChat(chat_uid=chat_uid)
        
        # Convert stored data to CursorChat
        return CursorChat.from_dict(data)
    
    def summarize_chat(self, chat: CursorChat) -> str:
        """
        Summarize the chat conversation.
        
        Uses OpenAI to generate a concise summary of the
        user-assistant conversation.
        
        Args:
            chat: CursorChat to summarize.
            
        Returns:
            Summary string.
        """
        if len(chat.messages) == 0:
            return "No messages to summarize."
        
        # Get conversation text
        conversation = chat.get_conversation_text()
        
        # Use OpenAI to summarize
        summary = self._openai.summarize(
            text=conversation,
            max_length=300,
            style="bullet",
        )
        
        self._current_summary = summary
        logger.info("Generated summary for chat %s (%d chars)", chat.chat_uid, len(summary))
        
        return summary
    
    def process_command(self, command: str, context: Optional[str] = None) -> CommandResult:
        """
        Process a voice command from the user.
        
        Recognizes commands like "stop", "forget", "spawn" and
        executes the appropriate action.
        
        Args:
            command: The voice command/instruction.
            context: Optional additional context.
            
        Returns:
            CommandResult with action and response.
        """
        # Use OpenAI to parse the command
        result = self._openai.process_instruction(command, context)
        
        action = result.get("action", "unknown")
        parameters = result.get("parameters", {})
        response = result.get("response", "I didn't understand that command.")
        
        # Execute known commands
        if action == "stop":
            return self._handle_stop(parameters)
        elif action == "forget":
            return self._handle_forget(parameters)
        elif action == "spawn":
            return self._handle_spawn(parameters)
        elif action == "summarize":
            return self._handle_summarize(parameters)
        elif action == "status":
            return self._handle_status(parameters)
        else:
            return CommandResult(
                action="unknown",
                parameters=parameters,
                response=response,
                success=False,
            )
    
    def _handle_stop(self, parameters: Dict) -> CommandResult:
        """Handle the stop command."""
        logger.info("Executing STOP command for minion %s", self.minion_id)
        return CommandResult(
            action="stop",
            parameters=parameters,
            response="Okay, stopping the current operation.",
            success=True,
        )
    
    def _handle_forget(self, parameters: Dict) -> CommandResult:
        """Handle the forget command."""
        logger.info("Executing FORGET command for minion %s", self.minion_id)
        self._current_summary = None
        return CommandResult(
            action="forget",
            parameters=parameters,
            response="I've cleared my memory. What would you like me to do?",
            success=True,
        )
    
    def _handle_spawn(self, parameters: Dict) -> CommandResult:
        """Handle the spawn command."""
        logger.info("Executing SPAWN command for minion %s", self.minion_id)
        new_minion_id = parameters.get("minion_id", f"minion_{datetime.now().timestamp()}")
        return CommandResult(
            action="spawn",
            parameters={"new_minion_id": new_minion_id},
            response=f"Creating a new minion. Stand by.",
            success=True,
        )
    
    def _handle_summarize(self, parameters: Dict) -> CommandResult:
        """Handle the summarize command."""
        logger.info("Executing SUMMARIZE command for minion %s", self.minion_id)
        
        if self._current_summary:
            return CommandResult(
                action="summarize",
                parameters=parameters,
                response=f"Here's what's been happening: {self._current_summary}",
                success=True,
            )
        else:
            # Load and summarize the chat
            chat = self.load_chat(self.chat_uid)
            if chat:
                summary = self.summarize_chat(chat)
                return CommandResult(
                    action="summarize",
                    parameters=parameters,
                    response=f"Here's what's been happening: {summary}",
                    success=True,
                )
            else:
                return CommandResult(
                    action="summarize",
                    parameters=parameters,
                    response="I don't have any conversation to summarize yet.",
                    success=False,
                )
    
    def _handle_status(self, parameters: Dict) -> CommandResult:
        """Handle the status command."""
        logger.info("Executing STATUS command for minion %s", self.minion_id)
        return CommandResult(
            action="status",
            parameters=parameters,
            response=f"I'm monitoring chat {self.chat_uid}. Everything is running smoothly.",
            success=True,
        )
    
    def get_current_summary(self) -> Optional[str]:
        """
        Get the most recent summary.
        
        Returns:
            Current summary or None.
        """
        return self._current_summary
    
    def update_from_new_messages(self, new_messages: List[ChatMessage]) -> Optional[str]:
        """
        Update summary with new messages.
        
        Called when CursorListener detects new messages.
        
        Args:
            new_messages: List of new messages to incorporate.
            
        Returns:
            Updated summary or None.
        """
        if not new_messages:
            return None
        
        # Create a mini-chat with just new messages
        temp_chat = CursorChat(
            chat_uid=self.chat_uid,
            messages=new_messages,
        )
        
        # Generate update summary
        update = self.summarize_chat(temp_chat)
        
        # Combine with existing summary
        if self._current_summary:
            # Use OpenAI to merge summaries
            messages = [
                {"role": "user", "content": f"Previous summary:\n{self._current_summary}\n\nNew updates:\n{update}\n\nPlease provide a combined, updated summary."}
            ]
            result = self._openai.complete(
                messages,
                system_prompt="You are a helpful assistant that merges summaries. Keep the result concise.",
                temperature=0.5,
            )
            self._current_summary = result.content
        else:
            self._current_summary = update
        
        return self._current_summary
