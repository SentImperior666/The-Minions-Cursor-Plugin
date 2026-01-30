"""
Integration tests for The Minions Cursor Plugin.

Tests the combined functionality of all components.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.minions.core import Minion, MinionManager, MinionState
from src.minions.cursor import CursorChat, ChatMessage, CursorDatabase
from src.minions.database import RedisDatabase
from src.minions.agent import MinionAgent, CommandResult
from src.minions.voice import MinionVoice
from src.minions.memory import MinionMemory


class TestRedisDatabase:
    """Tests for in-memory Redis fallback."""
    
    def test_connect_disconnect(self):
        """Test connecting and disconnecting."""
        redis = RedisDatabase(use_mock=True)
        
        assert redis.connect() is True
        assert redis.is_connected is True
        
        redis.disconnect()
        assert redis.is_connected is False
    
    def test_write_read(self):
        """Test writing and reading values."""
        redis = RedisDatabase(use_mock=True)
        redis.connect()
        
        # String
        assert redis.write("key1", "value1") is True
        assert redis.read("key1") == "value1"
        
        # Dict
        data = {"name": "test", "count": 42}
        assert redis.write("key2", data) is True
        assert redis.read("key2") == data
        
        # List
        items = [1, 2, 3]
        assert redis.write("key3", items) is True
        assert redis.read("key3") == items
        
        redis.disconnect()
    
    def test_exists_delete(self):
        """Test exists and delete operations."""
        redis = RedisDatabase(use_mock=True)
        redis.connect()
        
        redis.write("temp", "value")
        assert redis.exists("temp") is True
        
        assert redis.delete("temp") is True
        assert redis.exists("temp") is False
        
        redis.disconnect()
    
    def test_keys_pattern(self):
        """Test keys pattern matching."""
        redis = RedisDatabase(use_mock=True)
        redis.connect()
        
        redis.write("minion:1:info", {})
        redis.write("minion:2:info", {})
        redis.write("chat:abc:messages", [])
        
        minion_keys = redis.keys("minion:*")
        assert len(minion_keys) == 2
        
        chat_keys = redis.keys("chat:*")
        assert len(chat_keys) == 1
        
        redis.disconnect()


class TestChatMessage:
    """Tests for ChatMessage data type."""
    
    def test_create_message(self):
        """Test creating a chat message."""
        msg = ChatMessage(
            id="msg-1",
            role="user",
            content="Hello!",
            timestamp=datetime.now(),
            chat_uid="chat-1",
        )
        
        assert msg.id == "msg-1"
        assert msg.role == "user"
        assert msg.content == "Hello!"
    
    def test_invalid_role(self):
        """Test that invalid role raises error."""
        with pytest.raises(ValueError):
            ChatMessage(
                id="msg-1",
                role="invalid",
                content="Test",
                timestamp=datetime.now(),
                chat_uid="chat-1",
            )
    
    def test_to_dict_from_dict(self):
        """Test serialization roundtrip."""
        original = ChatMessage(
            id="msg-1",
            role="assistant",
            content="Response",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            chat_uid="chat-1",
        )
        
        data = original.to_dict()
        restored = ChatMessage.from_dict(data)
        
        assert restored.id == original.id
        assert restored.role == original.role
        assert restored.content == original.content


class TestCursorChat:
    """Tests for CursorChat data type."""
    
    def test_create_empty_chat(self):
        """Test creating an empty chat."""
        chat = CursorChat(uid="chat-1")
        
        assert chat.uid == "chat-1"
        assert chat.message_count == 0
        assert chat.is_empty is True
    
    def test_add_message(self):
        """Test adding messages to chat."""
        chat = CursorChat(uid="chat-1")
        
        msg = ChatMessage(
            id="msg-1",
            role="user",
            content="Hello",
            timestamp=datetime.now(),
            chat_uid="chat-1",
        )
        chat.add_message(msg)
        
        assert chat.message_count == 1
        assert chat.is_empty is False
    
    def test_get_latest_message(self):
        """Test getting latest message."""
        chat = CursorChat(uid="chat-1")
        
        chat.add_message(ChatMessage(
            id="msg-1", role="user", content="First",
            timestamp=datetime(2024, 1, 1), chat_uid="chat-1"
        ))
        chat.add_message(ChatMessage(
            id="msg-2", role="assistant", content="Second",
            timestamp=datetime(2024, 1, 2), chat_uid="chat-1"
        ))
        
        latest = chat.get_latest_message()
        assert latest.content == "Second"


class TestMinionMemory:
    """Tests for MinionMemory."""
    
    def test_init_new_minion(self):
        """Test initializing memory for new minion."""
        redis = RedisDatabase(use_mock=True)
        redis.connect()
        
        memory = MinionMemory.init("minion-1", "chat-1", redis)
        
        assert memory.exists() is True
        
        redis.disconnect()
    
    def test_save_and_get_summaries(self):
        """Test saving and retrieving summaries."""
        redis = RedisDatabase(use_mock=True)
        redis.connect()
        
        memory = MinionMemory.init("minion-1", "chat-1", redis)
        
        memory.save_summary("First summary")
        memory.save_summary("Second summary")
        
        summaries = memory.get_summaries()
        assert len(summaries) == 2
        assert summaries[0] == "First summary"
        
        latest = memory.get_latest_summary()
        assert latest == "Second summary"
        
        redis.disconnect()


class TestMinionAgent:
    """Tests for MinionAgent."""
    
    def test_process_stop_command(self):
        """Test processing stop command."""
        agent = MinionAgent("minion-1", "chat-1")
        
        result = agent.process_command("stop")
        
        assert result.action == "stop"
        assert result.success is True
    
    def test_process_forget_command(self):
        """Test processing forget command."""
        agent = MinionAgent("minion-1", "chat-1")
        
        result = agent.process_command("forget everything")
        
        assert result.action == "forget"
        assert result.success is True
    
    def test_process_spawn_command(self):
        """Test processing spawn command."""
        agent = MinionAgent("minion-1", "chat-1")
        
        result = agent.process_command("spawn a new minion")
        
        assert result.action == "spawn"
        assert result.success is True
        assert "new_minion_id" in result.parameters


class TestMinion:
    """Tests for Minion class."""
    
    def test_create_name(self):
        """Test generating minion names."""
        name1 = Minion.create_name()
        name2 = Minion.create_name()
        
        # Names should follow pattern "Name-Number"
        assert "-" in name1
        assert "-" in name2
    
    def test_generate_id(self):
        """Test generating minion IDs."""
        id1 = Minion._generate_id()
        id2 = Minion._generate_id()
        
        assert id1.startswith("minion_")
        assert id2.startswith("minion_")
        assert id1 != id2
    
    def test_get_state(self):
        """Test getting minion state."""
        minion = Minion(
            minion_id="test-minion",
            chat_uid="test-chat",
            name="Bob-42",
        )
        
        state = minion.get_state()
        
        assert isinstance(state, MinionState)
        assert state.minion_id == "test-minion"
        assert state.name == "Bob-42"
        assert state.is_active is True
    
    def test_stop(self):
        """Test stopping a minion."""
        minion = Minion(
            minion_id="test-minion",
            chat_uid="test-chat",
        )
        
        assert minion.is_active() is True
        
        minion.stop()
        
        assert minion.is_active() is False


class TestMinionManager:
    """Tests for MinionManager."""
    
    def test_init(self):
        """Test initializing manager."""
        redis = RedisDatabase(use_mock=True)
        
        manager = MinionManager(redis_db=redis, auto_spawn=True)
        
        assert manager.is_running is False
        assert len(manager.get_all_minions()) == 0
    
    def test_get_minion(self):
        """Test getting minion by chat UID."""
        redis = RedisDatabase(use_mock=True)
        manager = MinionManager(redis_db=redis)
        
        # No minions yet
        assert manager.get_minion("nonexistent") is None
