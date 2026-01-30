"""
MinionAgent - LLM agent for chat summarization and command processing.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .api import OpenAIAPI
from .cursor import CursorChat, ChatMessage

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result from processing a voice command."""
    action: str  # 'stop', 'forget', 'spawn', 'query', 'unknown'
    response: str
    success: bool
    parameters: Dict[str, Any]


class MinionAgent:
    """
    LLM agent that summarizes Cursor chats and processes commands.
    
    Capabilities:
    - Summarize chat history
    - Process voice commands (stop, forget, spawn)
    - Answer questions about the codebase
    """
    
    COMMANDS = {
        'stop': ['stop', 'end', 'quit', 'exit', 'bye', 'goodbye'],
        'forget': ['forget', 'clear', 'reset', 'erase'],
        'spawn': ['spawn', 'create', 'new minion', 'clone'],
    }
    
    def __init__(
        self,
        minion_id: str,
        chat_uid: str,
        openai_api: Optional[OpenAIAPI] = None,
        redis_db: Optional[Any] = None,
    ):
        self.minion_id = minion_id
        self.chat_uid = chat_uid
        self._openai = openai_api or OpenAIAPI()
        self._redis_db = redis_db
        self._current_summary: Optional[str] = None
        self._messages: List[ChatMessage] = []
        self._last_summarized_count: int = 0
    
    @classmethod
    def init(
        cls,
        minion_id: str,
        chat_uid: str,
        redis_db: Optional[Any] = None,
    ) -> 'MinionAgent':
        """
        Initialize a MinionAgent and load existing chat.
        
        Args:
            minion_id: Unique minion identifier.
            chat_uid: Chat UID to monitor.
            redis_db: Optional Redis database instance.
            
        Returns:
            Initialized MinionAgent.
        """
        agent = cls(minion_id, chat_uid, redis_db=redis_db)
        
        # Load chat from Redis if available
        chat = agent.load_chat(chat_uid)
        if chat:
            agent._messages = chat.messages
            # Summarize the initial chat
            if chat.messages:
                summary = agent.summarize_chat(chat)
                agent._current_summary = summary
                agent._last_summarized_count = len(chat.messages)
        
        logger.info("MinionAgent initialized for minion %s, chat %s", minion_id, chat_uid)
        return agent
    
    def load_chat(self, chat_uid: str) -> Optional[CursorChat]:
        """
        Load chat from Redis database.
        
        Args:
            chat_uid: Chat UID to load.
            
        Returns:
            CursorChat if found, None otherwise.
        """
        if not self._redis_db:
            return None
        
        try:
            messages_data = self._redis_db.read(f"chat:{chat_uid}:messages")
            metadata = self._redis_db.read(f"chat:{chat_uid}:metadata")
            
            if not messages_data:
                return None
            
            messages = [
                ChatMessage.from_dict(m) if isinstance(m, dict) else m
                for m in messages_data
            ]
            
            return CursorChat(
                uid=chat_uid,
                messages=messages,
                title=metadata.get('title') if metadata else None,
                workspace_path=metadata.get('workspace_path') if metadata else None,
            )
        except Exception as e:
            logger.error("Failed to load chat %s: %s", chat_uid, e)
            return None
    
    def summarize_chat(self, chat: CursorChat) -> str:
        """
        Summarize a chat conversation.
        
        Args:
            chat: CursorChat to summarize.
            
        Returns:
            Summary string.
        """
        if chat.is_empty:
            return "No messages to summarize."
        
        # Build conversation text
        conversation = []
        for msg in chat.messages:
            role = "User" if msg.role == "user" else "Assistant"
            conversation.append(f"{role}: {msg.content}")
        
        text = "\n\n".join(conversation)
        
        # Use OpenAI to summarize
        if self._openai.is_configured:
            summary = self._openai.summarize_text(
                text,
                max_length=150,
                context="This is a conversation between a user and an AI coding assistant in Cursor IDE."
            )
            if summary:
                return summary
        
        # Fallback: Simple extractive summary
        return self._simple_summary(chat)
    
    def _simple_summary(self, chat: CursorChat) -> str:
        """Create a simple summary without LLM."""
        user_msgs = chat.get_user_messages()
        if not user_msgs:
            return "Empty conversation."
        
        # Get first and last user messages
        first = user_msgs[0].content[:100]
        summary = f"Conversation started with: '{first}...'"
        
        if len(user_msgs) > 1:
            last = user_msgs[-1].content[:100]
            summary += f" Latest topic: '{last}...'"
        
        summary += f" ({chat.message_count} total messages)"
        return summary
    
    def get_current_summary(self) -> Optional[str]:
        """Get the current chat summary."""
        return self._current_summary
    
    def process_new_message(self, message: ChatMessage) -> None:
        """
        Process a new message and update summary if needed.
        
        Args:
            message: New message to process.
        """
        self._messages.append(message)
        
        # Update summary every 5 new messages
        if len(self._messages) - self._last_summarized_count >= 5:
            chat = CursorChat(
                uid=self.chat_uid,
                messages=self._messages,
            )
            self._current_summary = self.summarize_chat(chat)
            self._last_summarized_count = len(self._messages)
    
    def process_command(self, command: str) -> CommandResult:
        """
        Process a voice command.
        
        Args:
            command: Voice command text.
            
        Returns:
            CommandResult with action and response.
        """
        command_lower = command.lower().strip()
        
        # Check for known commands
        for action, keywords in self.COMMANDS.items():
            for keyword in keywords:
                if keyword in command_lower:
                    return self._execute_command(action, command)
        
        # If not a known command, treat as a query
        return self._handle_query(command)
    
    def _execute_command(self, action: str, raw_command: str) -> CommandResult:
        """Execute a recognized command."""
        if action == 'stop':
            return CommandResult(
                action='stop',
                response="Okay, I'll stop monitoring this chat. Goodbye!",
                success=True,
                parameters={},
            )
        
        elif action == 'forget':
            return CommandResult(
                action='forget',
                response="I've cleared my memory of this conversation.",
                success=True,
                parameters={},
            )
        
        elif action == 'spawn':
            # Generate a new minion ID
            new_id = f"minion_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return CommandResult(
                action='spawn',
                response=f"I'm creating a new minion with ID {new_id}.",
                success=True,
                parameters={'new_minion_id': new_id},
            )
        
        return CommandResult(
            action='unknown',
            response="I didn't understand that command.",
            success=False,
            parameters={},
        )
    
    def _handle_query(self, query: str) -> CommandResult:
        """Handle a query about the codebase or chat."""
        # Use LLM to answer if available
        if self._openai.is_configured:
            context = self._current_summary or "No chat context available."
            
            result = self._openai.chat_completion([
                {
                    "role": "system",
                    "content": f"""You are a helpful coding assistant minion.
You have access to the following context about a coding session:
{context}

Answer the user's question based on this context. If you don't know, say so."""
                },
                {"role": "user", "content": query}
            ])
            
            if result:
                return CommandResult(
                    action='query',
                    response=result.content,
                    success=True,
                    parameters={'query': query},
                )
        
        return CommandResult(
            action='query',
            response="I'm sorry, I can't answer that question right now.",
            success=False,
            parameters={'query': query},
        )
    
    # Added from Victor's implementation (vgh workspace)
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
        
        # Add new messages to our list
        for msg in new_messages:
            self._messages.append(msg)
        
        # Create a mini-chat with just new messages
        temp_chat = CursorChat(
            uid=self.chat_uid,
            messages=new_messages,
        )
        
        # Generate update summary
        update = self.summarize_chat(temp_chat)
        
        # Combine with existing summary
        if self._current_summary:
            # Use OpenAI to merge summaries
            if self._openai.is_configured:
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
                # Simple concatenation
                self._current_summary = f"{self._current_summary}\n\nUpdate: {update}"
        else:
            self._current_summary = update
        
        self._last_summarized_count = len(self._messages)
        return self._current_summary
