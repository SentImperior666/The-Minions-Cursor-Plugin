"""
Tests for MinionAgent.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.minions.agent import MinionAgent, CommandResult
from src.minions.api.openai_api import OpenAIAPI, CompletionResult
from mocks.redis_mock import RedisDatabase
from mocks.cursor_mock import CursorChat, ChatMessage, MessageRole


@pytest.fixture
def redis():
    """Create a fresh Redis mock for each test."""
    db = RedisDatabase()
    db.clear()
    return db


@pytest.fixture
def mock_openai():
    """Create a mock OpenAI API."""
    api = Mock(spec=OpenAIAPI)
    api.summarize.return_value = "This is a test summary of the conversation."
    api.complete.return_value = CompletionResult(
        content="Test response",
        model="gpt-4o-mini",
        usage={"total_tokens": 100},
        finish_reason="stop",
    )
    api.process_instruction.return_value = {
        "action": "summarize",
        "parameters": {},
        "response": "Here's your summary.",
    }
    return api


@pytest.fixture
def sample_chat():
    """Create a sample chat for testing."""
    return CursorChat(
        chat_uid="test_chat",
        messages=[
            ChatMessage(role=MessageRole.USER, content="Hello, can you help me?"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Of course! What do you need?"),
            ChatMessage(role=MessageRole.USER, content="I need to fix a bug."),
            ChatMessage(role=MessageRole.ASSISTANT, content="Let me look at the code."),
        ],
    )


class TestMinionAgent:
    """Tests for MinionAgent class."""
    
    def test_init_basic(self, redis, mock_openai):
        """Test basic initialization."""
        agent = MinionAgent(
            minion_id="test",
            chat_uid="chat1",
            openai=mock_openai,
            redis=redis,
        )
        
        assert agent.minion_id == "test"
        assert agent.chat_uid == "chat1"
    
    def test_init_classmethod(self, redis, mock_openai):
        """Test init() classmethod loads and summarizes chat."""
        # Store a chat in Redis
        chat = CursorChat(
            chat_uid="chat1",
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test message"),
            ],
        )
        redis.write("chat:chat1", chat.to_dict())
        
        agent = MinionAgent.init(
            minion_id="test",
            chat_uid="chat1",
            openai=mock_openai,
            redis=redis,
        )
        
        mock_openai.summarize.assert_called_once()
        assert agent.get_current_summary() is not None
    
    def test_load_chat_existing(self, redis, mock_openai, sample_chat):
        """Test loading an existing chat."""
        redis.write(f"chat:{sample_chat.chat_uid}", sample_chat.to_dict())
        
        agent = MinionAgent("test", sample_chat.chat_uid, mock_openai, redis)
        loaded = agent.load_chat(sample_chat.chat_uid)
        
        assert loaded is not None
        assert loaded.chat_uid == sample_chat.chat_uid
        assert len(loaded.messages) == 4
    
    def test_load_chat_nonexistent(self, redis, mock_openai):
        """Test loading a nonexistent chat returns empty."""
        agent = MinionAgent("test", "nonexistent", mock_openai, redis)
        loaded = agent.load_chat("nonexistent")
        
        assert loaded is not None
        assert loaded.chat_uid == "nonexistent"
        assert len(loaded.messages) == 0
    
    def test_summarize_chat(self, redis, mock_openai, sample_chat):
        """Test chat summarization."""
        agent = MinionAgent("test", sample_chat.chat_uid, mock_openai, redis)
        summary = agent.summarize_chat(sample_chat)
        
        assert summary == "This is a test summary of the conversation."
        assert agent.get_current_summary() == summary
    
    def test_summarize_empty_chat(self, redis, mock_openai):
        """Test summarizing empty chat."""
        empty_chat = CursorChat(chat_uid="empty", messages=[])
        
        agent = MinionAgent("test", "empty", mock_openai, redis)
        summary = agent.summarize_chat(empty_chat)
        
        assert "No messages" in summary
        mock_openai.summarize.assert_not_called()
    
    def test_process_command_stop(self, redis, mock_openai):
        """Test processing stop command."""
        mock_openai.process_instruction.return_value = {
            "action": "stop",
            "parameters": {},
            "response": "Stopping.",
        }
        
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        result = agent.process_command("stop")
        
        assert isinstance(result, CommandResult)
        assert result.action == "stop"
        assert result.success is True
    
    def test_process_command_forget(self, redis, mock_openai):
        """Test processing forget command."""
        mock_openai.process_instruction.return_value = {
            "action": "forget",
            "parameters": {},
            "response": "Forgetting.",
        }
        
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        agent._current_summary = "Old summary"
        
        result = agent.process_command("forget everything")
        
        assert result.action == "forget"
        assert result.success is True
        assert agent.get_current_summary() is None
    
    def test_process_command_spawn(self, redis, mock_openai):
        """Test processing spawn command."""
        mock_openai.process_instruction.return_value = {
            "action": "spawn",
            "parameters": {"minion_id": "new_minion"},
            "response": "Spawning new minion.",
        }
        
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        result = agent.process_command("spawn a new helper")
        
        assert result.action == "spawn"
        assert result.success is True
        assert "new_minion_id" in result.parameters
    
    def test_process_command_summarize(self, redis, mock_openai, sample_chat):
        """Test processing summarize command."""
        mock_openai.process_instruction.return_value = {
            "action": "summarize",
            "parameters": {},
            "response": "Summarizing.",
        }
        
        redis.write(f"chat:{sample_chat.chat_uid}", sample_chat.to_dict())
        
        agent = MinionAgent("test", sample_chat.chat_uid, mock_openai, redis)
        result = agent.process_command("give me a summary")
        
        assert result.action == "summarize"
        assert result.success is True
    
    def test_process_command_status(self, redis, mock_openai):
        """Test processing status command."""
        mock_openai.process_instruction.return_value = {
            "action": "status",
            "parameters": {},
            "response": "Checking status.",
        }
        
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        result = agent.process_command("what's your status")
        
        assert result.action == "status"
        assert result.success is True
        assert "chat1" in result.response
    
    def test_process_command_unknown(self, redis, mock_openai):
        """Test processing unknown command."""
        mock_openai.process_instruction.return_value = {
            "action": "unknown",
            "parameters": {},
            "response": "I don't understand.",
        }
        
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        result = agent.process_command("do something weird")
        
        assert result.action == "unknown"
        assert result.success is False
    
    def test_update_from_new_messages(self, redis, mock_openai):
        """Test updating summary with new messages."""
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        agent._current_summary = "Previous summary"
        
        new_messages = [
            ChatMessage(role=MessageRole.USER, content="New message"),
            ChatMessage(role=MessageRole.ASSISTANT, content="New response"),
        ]
        
        result = agent.update_from_new_messages(new_messages)
        
        assert result is not None
        mock_openai.summarize.assert_called()
    
    def test_update_from_empty_messages(self, redis, mock_openai):
        """Test updating with empty messages does nothing."""
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        result = agent.update_from_new_messages([])
        
        assert result is None
    
    def test_get_current_summary(self, redis, mock_openai):
        """Test getting current summary."""
        agent = MinionAgent("test", "chat1", mock_openai, redis)
        assert agent.get_current_summary() is None
        
        agent._current_summary = "Test summary"
        assert agent.get_current_summary() == "Test summary"
