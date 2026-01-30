"""
Tests for MinionMemory.
"""

import pytest
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.minions.memory import MinionMemory, MinionInfo
from mocks.redis_mock import RedisDatabase


@pytest.fixture
def redis():
    """Create a fresh Redis mock for each test."""
    db = RedisDatabase()
    db.clear()
    return db


@pytest.fixture
def memory(redis):
    """Create a MinionMemory instance for testing."""
    return MinionMemory("test_minion", "test_chat_uid", redis)


class TestMinionMemory:
    """Tests for MinionMemory class."""
    
    def test_init_creates_memory(self, redis):
        """Test that init() creates a new memory entry."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        
        assert memory.minion_id == "minion1"
        assert memory.chat_uid == "chat1"
        assert memory.exists()
    
    def test_init_clears_summaries_for_existing(self, redis):
        """Test that init() clears summaries for existing minion."""
        # Create minion and add summary
        memory1 = MinionMemory.init("minion1", "chat1", redis)
        memory1.save_summary("First summary")
        assert len(memory1.get_summaries()) == 1
        
        # Init again should clear summaries
        memory2 = MinionMemory.init("minion1", "chat1", redis)
        assert len(memory2.get_summaries()) == 0
    
    def test_save_and_get_name(self, redis):
        """Test saving and retrieving minion name."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        memory.save_name("Bob-42")
        
        info = memory.get_info()
        assert info.minion_name == "Bob-42"
    
    def test_save_and_get_voice(self, redis):
        """Test saving and retrieving voice info."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        
        # Create a mock voice object
        class MockVoice:
            name = "Test Voice"
            description = "A test voice"
            voice_id = "voice_123"
            config = {"stability": 0.5}
        
        memory.save_voice(MockVoice())
        
        voice_info = memory.get_voice_info()
        assert voice_info["voice_name"] == "Test Voice"
        assert voice_info["voice_id"] == "voice_123"
    
    def test_save_and_get_summaries(self, redis):
        """Test saving and retrieving summaries."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        
        memory.save_summary("Summary 1")
        memory.save_summary("Summary 2")
        memory.save_summary("Summary 3")
        
        summaries = memory.get_summaries()
        assert len(summaries) == 3
        assert summaries[0] == "Summary 1"
        assert summaries[2] == "Summary 3"
    
    def test_get_summaries_with_timestamps(self, redis):
        """Test getting summaries with timestamps."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        memory.save_summary("Test summary")
        
        summaries = memory.get_summaries_with_timestamps()
        assert len(summaries) == 1
        assert "summary" in summaries[0]
        assert "timestamp" in summaries[0]
    
    def test_get_latest_summary(self, redis):
        """Test getting the latest summary."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        
        memory.save_summary("First")
        memory.save_summary("Second")
        memory.save_summary("Latest")
        
        assert memory.get_latest_summary() == "Latest"
    
    def test_get_latest_summary_empty(self, redis):
        """Test getting latest summary when none exist."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        assert memory.get_latest_summary() is None
    
    def test_exists(self, redis):
        """Test exists() method."""
        memory = MinionMemory("nonexistent", "chat1", redis)
        assert not memory.exists()
        
        MinionMemory.init("exists", "chat1", redis)
        memory2 = MinionMemory("exists", "chat1", redis)
        assert memory2.exists()
    
    def test_delete(self, redis):
        """Test deleting minion data."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        memory.save_summary("Test")
        
        assert memory.exists()
        
        memory.delete()
        assert not memory.exists()
        assert len(memory.get_summaries()) == 0
    
    def test_update_info(self, redis):
        """Test updating info fields."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        
        memory.update_info(
            minion_name="Updated Name",
            voice_id="new_voice_id",
        )
        
        info = memory.get_info()
        assert info.minion_name == "Updated Name"
        assert info.voice_id == "new_voice_id"
    
    def test_get_info_returns_minion_info(self, redis):
        """Test that get_info returns MinionInfo dataclass."""
        memory = MinionMemory.init("minion1", "chat1", redis)
        memory.save_name("TestBot")
        
        info = memory.get_info()
        
        assert isinstance(info, MinionInfo)
        assert info.minion_id == "minion1"
        assert info.chat_uid == "chat1"
        assert info.minion_name == "TestBot"
        assert isinstance(info.created_at, datetime)
    
    def test_get_info_nonexistent(self, redis):
        """Test get_info for nonexistent minion."""
        memory = MinionMemory("nonexistent", "chat1", redis)
        assert memory.get_info() is None
    
    def test_multiple_minions(self, redis):
        """Test handling multiple minions in same Redis."""
        memory1 = MinionMemory.init("minion1", "chat1", redis)
        memory2 = MinionMemory.init("minion2", "chat2", redis)
        
        memory1.save_name("Bob")
        memory2.save_name("Kevin")
        
        memory1.save_summary("Summary for minion 1")
        memory2.save_summary("Summary for minion 2")
        
        assert memory1.get_info().minion_name == "Bob"
        assert memory2.get_info().minion_name == "Kevin"
        assert memory1.get_summaries()[0] == "Summary for minion 1"
        assert memory2.get_summaries()[0] == "Summary for minion 2"
