"""
Tests for RedisDatabase.

Uses fakeredis for testing without a real Redis instance.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

import fakeredis

from src.minions.database.redis_database import RedisDatabase
from src.minions.database.data_types import MinionInfo, VoiceData, ChatMessageData


class TestRedisDatabase:
    """Test suite for RedisDatabase."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a fakeredis instance."""
        return fakeredis.FakeRedis(decode_responses=True)
    
    @pytest.fixture
    def db(self, mock_redis):
        """Create a RedisDatabase with mocked redis client."""
        db = RedisDatabase()
        db._client = mock_redis
        db._connected = True
        return db
    
    def test_connect_success(self):
        """Test successful connection."""
        db = RedisDatabase()
        with patch('redis.Redis') as mock_redis_cls:
            mock_client = MagicMock()
            mock_redis_cls.return_value = mock_client
            
            result = db.connect()
            
            assert result is True
            assert db.is_connected is True
    
    def test_connect_failure(self):
        """Test connection failure."""
        db = RedisDatabase()
        with patch('redis.Redis') as mock_redis_cls:
            from redis.exceptions import ConnectionError
            mock_client = MagicMock()
            mock_client.ping.side_effect = ConnectionError("Connection refused")
            mock_redis_cls.return_value = mock_client
            
            result = db.connect()
            
            assert result is False
            assert db.is_connected is False
    
    def test_disconnect(self, db):
        """Test disconnection."""
        db.disconnect()
        
        assert db.is_connected is False
        assert db._client is None
    
    def test_write_and_read_string(self, db):
        """Test writing and reading a string."""
        result = db.write("test_key", "test_value")
        
        assert result is True
        assert db.read("test_key") == "test_value"
    
    def test_write_and_read_dict(self, db):
        """Test writing and reading a dictionary."""
        data = {"name": "test", "value": 123}
        
        result = db.write("test_dict", data)
        
        assert result is True
        assert db.read("test_dict") == data
    
    def test_read_nonexistent_key(self, db):
        """Test reading a key that doesn't exist."""
        result = db.read("nonexistent")
        
        assert result is None
    
    def test_delete(self, db):
        """Test deleting a key."""
        db.write("to_delete", "value")
        
        result = db.delete("to_delete")
        
        assert result is True
        assert db.read("to_delete") is None
    
    def test_delete_nonexistent(self, db):
        """Test deleting a nonexistent key."""
        result = db.delete("nonexistent")
        
        assert result is False
    
    def test_exists(self, db):
        """Test checking key existence."""
        db.write("exists_key", "value")
        
        assert db.exists("exists_key") is True
        assert db.exists("nonexistent") is False
    
    def test_keys_pattern(self, db):
        """Test getting keys by pattern."""
        db.write("prefix:1", "a")
        db.write("prefix:2", "b")
        db.write("other:1", "c")
        
        result = db.keys("prefix:*")
        
        assert len(result) == 2
        assert "prefix:1" in result
        assert "prefix:2" in result
    
    def test_list_push_and_get(self, db):
        """Test list operations."""
        db.list_push("my_list", "item1")
        db.list_push("my_list", "item2")
        
        result = db.list_get("my_list")
        
        assert result == ["item1", "item2"]
    
    def test_list_length(self, db):
        """Test list length."""
        db.list_push("my_list", "item1")
        db.list_push("my_list", "item2")
        
        assert db.list_length("my_list") == 2
    
    def test_list_clear(self, db):
        """Test clearing a list."""
        db.list_push("my_list", "item1")
        db.list_clear("my_list")
        
        assert db.list_get("my_list") == []


class TestRedisDatabaseMinionOperations:
    """Test suite for high-level minion operations."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a fakeredis instance."""
        return fakeredis.FakeRedis(decode_responses=True)
    
    @pytest.fixture
    def db(self, mock_redis):
        """Create a RedisDatabase with mocked redis client."""
        db = RedisDatabase()
        db._client = mock_redis
        db._connected = True
        return db
    
    def test_save_and_get_minion_info(self, db):
        """Test saving and retrieving minion info."""
        info = MinionInfo(
            minion_id="minion_123",
            chat_uid="chat_456",
            minion_name="Bob"
        )
        
        result = db.save_minion_info(info)
        
        assert result is True
        
        retrieved = db.get_minion_info("minion_123")
        
        assert retrieved is not None
        assert retrieved.minion_id == "minion_123"
        assert retrieved.chat_uid == "chat_456"
        assert retrieved.minion_name == "Bob"
    
    def test_get_nonexistent_minion(self, db):
        """Test getting a nonexistent minion."""
        result = db.get_minion_info("nonexistent")
        
        assert result is None
    
    def test_save_and_get_voice_data(self, db):
        """Test saving and retrieving voice data."""
        voice = VoiceData(
            voice_name="Bob's Voice",
            voice_description="A friendly voice",
            elevenlabs_voice_id="el_123"
        )
        
        result = db.save_voice_data("minion_123", voice)
        
        assert result is True
        
        retrieved = db.get_voice_data("minion_123")
        
        assert retrieved is not None
        assert retrieved.voice_name == "Bob's Voice"
        assert retrieved.elevenlabs_voice_id == "el_123"
    
    def test_add_and_get_summaries(self, db):
        """Test adding and retrieving summaries."""
        db.add_summary("minion_123", "First summary")
        db.add_summary("minion_123", "Second summary")
        
        summaries = db.get_summaries("minion_123")
        
        assert len(summaries) == 2
        assert "First summary" in summaries
        assert "Second summary" in summaries
    
    def test_clear_summaries(self, db):
        """Test clearing summaries."""
        db.add_summary("minion_123", "Summary")
        db.clear_summaries("minion_123")
        
        summaries = db.get_summaries("minion_123")
        
        assert summaries == []
    
    def test_add_and_get_chat_messages(self, db):
        """Test adding and retrieving chat messages."""
        msg1 = ChatMessageData(
            role="user",
            content="Hello",
            message_id="msg_1"
        )
        msg2 = ChatMessageData(
            role="assistant",
            content="Hi there!",
            message_id="msg_2"
        )
        
        db.add_chat_message("chat_123", msg1)
        db.add_chat_message("chat_123", msg2)
        
        messages = db.get_chat_messages("chat_123")
        
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
    
    def test_get_all_minion_ids(self, db):
        """Test getting all minion IDs."""
        info1 = MinionInfo("minion_1", "chat_1", "Alice")
        info2 = MinionInfo("minion_2", "chat_2", "Bob")
        
        db.save_minion_info(info1)
        db.save_minion_info(info2)
        
        minion_ids = db.get_all_minion_ids()
        
        assert "minion_1" in minion_ids
        assert "minion_2" in minion_ids
    
    def test_get_all_chat_uids(self, db):
        """Test getting all chat UIDs."""
        msg = ChatMessageData(role="user", content="Hello")
        
        db.add_chat_message("chat_1", msg)
        db.add_chat_message("chat_2", msg)
        
        chat_uids = db.get_all_chat_uids()
        
        assert "chat_1" in chat_uids
        assert "chat_2" in chat_uids


class TestDataTypes:
    """Test suite for data types serialization."""
    
    def test_minion_info_serialization(self):
        """Test MinionInfo JSON serialization."""
        info = MinionInfo(
            minion_id="123",
            chat_uid="456",
            minion_name="Test"
        )
        
        json_str = info.to_json()
        restored = MinionInfo.from_json(json_str)
        
        assert restored.minion_id == info.minion_id
        assert restored.chat_uid == info.chat_uid
        assert restored.minion_name == info.minion_name
    
    def test_voice_data_serialization(self):
        """Test VoiceData JSON serialization."""
        voice = VoiceData(
            voice_name="Test Voice",
            voice_description="A test voice",
            elevenlabs_voice_id="el_123"
        )
        
        json_str = voice.to_json()
        restored = VoiceData.from_json(json_str)
        
        assert restored.voice_name == voice.voice_name
        assert restored.voice_description == voice.voice_description
        assert restored.elevenlabs_voice_id == voice.elevenlabs_voice_id
    
    def test_chat_message_serialization(self):
        """Test ChatMessageData JSON serialization."""
        msg = ChatMessageData(
            role="user",
            content="Hello world",
            message_id="msg_123"
        )
        
        json_str = msg.to_json()
        restored = ChatMessageData.from_json(json_str)
        
        assert restored.role == msg.role
        assert restored.content == msg.content
        assert restored.message_id == msg.message_id
