"""
Tests for the main Minion class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.minions.minion import Minion, MinionState, MINION_NAMES
from src.minions.agent import MinionAgent
from src.minions.voice import MinionVoice
from src.minions.memory import MinionMemory
from src.minions.api.twilio_api import TwilioAPI, CallInfo, CallStatus
from mocks.redis_mock import RedisDatabase


@pytest.fixture
def redis():
    """Create a fresh Redis mock for each test."""
    db = RedisDatabase()
    db.clear()
    return db


@pytest.fixture
def mock_agent():
    """Create a mock MinionAgent."""
    agent = Mock(spec=MinionAgent)
    agent.get_current_summary.return_value = "Test summary"
    agent.process_command.return_value = Mock(
        action="summarize",
        response="Here's the summary",
        success=True,
        parameters={},
    )
    return agent


@pytest.fixture
def mock_voice():
    """Create a mock MinionVoice."""
    voice = Mock(spec=MinionVoice)
    voice.voice_id = "test_voice_id"
    voice.name = "TestVoice"
    voice.text_to_speech.return_value = b"audio_data"
    return voice


@pytest.fixture
def mock_memory(redis):
    """Create a mock MinionMemory."""
    memory = Mock(spec=MinionMemory)
    memory.minion_id = "test_minion"
    memory.chat_uid = "test_chat"
    memory.exists.return_value = True
    memory.get_info.return_value = Mock(
        minion_name="TestBot",
        created_at=datetime.now(),
    )
    memory.get_summaries.return_value = ["Summary 1", "Summary 2"]
    memory.get_voice_info.return_value = {
        "voice_id": "test_voice_id",
        "voice_name": "TestVoice",
    }
    return memory


class TestMinion:
    """Tests for Minion class."""
    
    def test_init_basic(self):
        """Test basic initialization."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            name="Bob",
        )
        
        assert minion.minion_id == "test"
        assert minion.chat_uid == "chat1"
        assert minion.name == "Bob"
        assert minion.is_active()
    
    def test_init_with_components(self, mock_agent, mock_voice, mock_memory):
        """Test initialization with all components."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            name="Bob",
            agent=mock_agent,
            voice=mock_voice,
            memory=mock_memory,
        )
        
        assert minion.agent is mock_agent
        assert minion.voice is mock_voice
        assert minion.memory is mock_memory
    
    def test_generate_id(self):
        """Test ID generation."""
        id1 = Minion._generate_id()
        id2 = Minion._generate_id()
        
        assert id1.startswith("minion_")
        assert id2.startswith("minion_")
        assert id1 != id2  # Should be unique
    
    def test_create_name(self):
        """Test name creation."""
        name = Minion.create_name()
        
        parts = name.split("-")
        assert len(parts) == 2
        assert parts[0] in MINION_NAMES
        assert parts[1].isdigit()
    
    def test_spawn_new_minion(self, redis):
        """Test spawning a new minion."""
        with patch.object(Minion, 'create') as mock_create:
            mock_create.return_value = Mock(spec=Minion)
            
            minion = Minion.spawn("chat1", "new_minion")
            
            mock_create.assert_called_once_with("new_minion", "chat1")
    
    def test_spawn_existing_minion(self, redis):
        """Test spawning loads existing minion."""
        # Create a minion first
        MinionMemory.init("existing", "chat1", redis)
        
        with patch.object(Minion, 'load') as mock_load:
            mock_load.return_value = Mock(spec=Minion)
            
            minion = Minion.spawn("chat1", "existing")
            
            mock_load.assert_called_once_with("existing", "chat1")
    
    def test_spawn_generates_id(self, redis):
        """Test spawn generates ID when not provided."""
        with patch.object(Minion, 'create') as mock_create:
            mock_create.return_value = Mock(spec=Minion)
            
            Minion.spawn("chat1")
            
            call_args = mock_create.call_args[0]
            assert call_args[0].startswith("minion_")
    
    def test_get_summary(self, mock_agent):
        """Test getting summary."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            agent=mock_agent,
        )
        
        summary = minion.get_summary()
        assert summary == "Test summary"
    
    def test_get_summary_no_agent(self):
        """Test getting summary without agent."""
        minion = Minion(minion_id="test", chat_uid="chat1")
        summary = minion.get_summary()
        
        assert "not initialized" in summary.lower()
    
    def test_speak(self, mock_voice):
        """Test text to speech."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            voice=mock_voice,
        )
        
        audio = minion.speak("Hello world")
        
        assert audio == b"audio_data"
        mock_voice.text_to_speech.assert_called_once_with("Hello world")
    
    def test_speak_no_voice(self):
        """Test speak without voice returns empty bytes."""
        minion = Minion(minion_id="test", chat_uid="chat1")
        audio = minion.speak("Hello")
        
        assert audio == b""
    
    def test_process_command(self, mock_agent, mock_memory):
        """Test command processing."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            agent=mock_agent,
            memory=mock_memory,
        )
        
        result = minion.process_command("summarize")
        
        assert result["action"] == "summarize"
        assert result["success"] is True
    
    def test_process_command_stop(self, mock_agent, mock_memory):
        """Test stop command deactivates minion."""
        mock_agent.process_command.return_value = Mock(
            action="stop",
            response="Stopping",
            success=True,
            parameters={},
        )
        
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            agent=mock_agent,
            memory=mock_memory,
        )
        
        assert minion.is_active()
        minion.process_command("stop")
        assert not minion.is_active()
    
    def test_process_command_forget(self, mock_agent, mock_memory):
        """Test forget command clears memory."""
        mock_agent.process_command.return_value = Mock(
            action="forget",
            response="Forgetting",
            success=True,
            parameters={},
        )
        
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            agent=mock_agent,
            memory=mock_memory,
        )
        
        minion.process_command("forget")
        mock_memory._clear_summaries.assert_called_once()
    
    def test_process_command_no_agent(self):
        """Test command processing without agent."""
        minion = Minion(minion_id="test", chat_uid="chat1")
        result = minion.process_command("test")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_call_user(self):
        """Test initiating a phone call."""
        mock_twilio = Mock(spec=TwilioAPI)
        mock_twilio.initiate_call.return_value = CallInfo(
            call_sid="call_123",
            status=CallStatus.QUEUED,
            from_number="+15551234567",
            to_number="+15559876543",
        )
        
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            name="Bob",
            twilio=mock_twilio,
        )
        
        call = minion.call_user("+15559876543", "https://example.com/webhook")
        
        assert call.call_sid == "call_123"
        assert call.status == CallStatus.QUEUED
        mock_twilio.initiate_call.assert_called_once()
    
    def test_get_state(self, mock_agent, mock_voice, mock_memory):
        """Test getting minion state."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            name="TestBot",
            agent=mock_agent,
            voice=mock_voice,
            memory=mock_memory,
        )
        
        state = minion.get_state()
        
        assert isinstance(state, MinionState)
        assert state.minion_id == "test"
        assert state.chat_uid == "chat1"
        assert state.name == "TestBot"
        assert state.is_active is True
        assert state.has_voice is True
        assert state.summary_count == 2
    
    def test_stop(self, mock_agent):
        """Test stopping the minion."""
        minion = Minion(
            minion_id="test",
            chat_uid="chat1",
            agent=mock_agent,
        )
        
        assert minion.is_active()
        minion.stop()
        assert not minion.is_active()
    
    def test_repr(self):
        """Test string representation."""
        minion = Minion(
            minion_id="test_id",
            chat_uid="chat_uid",
            name="Bob",
        )
        
        repr_str = repr(minion)
        assert "test_id" in repr_str
        assert "Bob" in repr_str
        assert "chat_uid" in repr_str


class TestMinionIntegration:
    """Integration tests for Minion with real components."""
    
    def test_create_minion_integration(self, redis):
        """Test creating a minion with real components (mocked APIs)."""
        with patch('src.minions.voice.ElevenLabsAPI') as MockElevenLabs, \
             patch('src.minions.agent.OpenAIAPI') as MockOpenAI:
            
            # Setup mock returns
            mock_eleven = MockElevenLabs.return_value
            mock_eleven.design_voice.return_value = "gen_voice_id"
            mock_eleven.create_voice.return_value = Mock(voice_id="voice_123")
            
            mock_openai = MockOpenAI.return_value
            mock_openai.summarize.return_value = "Chat summary"
            
            # The actual test would require more setup
            # For now, just verify the pattern works
            memory = MinionMemory.init("test", "chat1", redis)
            assert memory.exists()
    
    def test_load_minion_integration(self, redis):
        """Test loading a minion with real components."""
        # First create the minion data
        memory = MinionMemory.init("test", "chat1", redis)
        memory.save_name("TestBot")
        memory.save_summary("Previous summary")
        
        # Verify data is stored
        assert memory.exists()
        assert memory.get_info().minion_name == "TestBot"
