# Victor's Implementation Plan - Task 2

## Overview
Implementing the core Minion logic: MinionAgent, MinionVoice, MinionMemory, and API callers.

## Directory Structure

```
vgh/
├── src/
│   └── minions/
│       ├── __init__.py
│       ├── minion.py           # Main Minion class
│       ├── agent.py            # MinionAgent class
│       ├── voice.py            # MinionVoice class
│       ├── memory.py           # MinionMemory class
│       └── api/
│           ├── __init__.py
│           ├── openai_api.py   # OpenAI interface
│           ├── elevenlabs_api.py # ElevenLabs interface
│           └── twilio_api.py   # Twilio interface
├── tests/
│   ├── __init__.py
│   ├── test_minion.py
│   ├── test_agent.py
│   ├── test_voice.py
│   ├── test_memory.py
│   └── test_apis.py
├── mocks/
│   ├── __init__.py
│   ├── redis_mock.py          # Mock for RedisDatabase (Xavier's task)
│   └── cursor_mock.py         # Mock for CursorChat/Database (Marcus's task)
├── configs/
│   └── voice_config.yaml      # Default voice configuration
├── requirements.txt
├── pytest.ini
└── README.md
```

## Implementation Order

### Phase 1: Setup & Mocks
1. Create project structure
2. Create mock interfaces for dependencies (Redis, Cursor)
3. Set up pytest configuration

### Phase 2: API Clients
1. `OpenAIAPI` - Chat completion, summarization
2. `ElevenLabsAPI` - Voice design, creation, TTS, STT
3. `TwilioAPI` - Outbound call initiation

### Phase 3: Core Components
1. `MinionMemory` - State management using Redis mock
2. `MinionVoice` - Voice creation and management
3. `MinionAgent` - LLM agent for summarization
4. `Minion` - Main orchestration class

### Phase 4: Testing
1. Unit tests for all APIs
2. Unit tests for all components
3. Integration tests

## Component Specifications

### Minion Class
```python
class Minion:
    @classmethod
    def spawn(cls, chat_uid: str, minion_id: str = None, persist: bool = True) -> 'Minion'
    
    @classmethod  
    def create(cls, minion_id: str, chat_uid: str) -> 'Minion'
    
    @classmethod
    def load(cls, minion_id: str, chat_uid: str) -> 'Minion'
    
    def create_name(self) -> str
```

### MinionAgent Class
```python
class MinionAgent:
    @classmethod
    def init(cls, minion_id: str, chat_uid: str) -> 'MinionAgent'
    
    def load_chat(self, chat_uid: str) -> 'CursorChat'
    
    def summarize_chat(self, chat: 'CursorChat') -> str
    
    def process_command(self, command: str) -> Any
```

### MinionVoice Class
```python
class MinionVoice:
    @classmethod
    def init(cls, minion_id: str, minion_name: str, config: Dict = None) -> 'MinionVoice'
    
    @classmethod
    def load(cls, minion_id: str) -> 'MinionVoice'
    
    def load_config(self, config: Dict = None) -> None
    
    def create_name(self, minion_name: str) -> str
    
    def text_to_speech(self, text: str) -> bytes
    
    def speech_to_text(self, audio: bytes) -> str
```

### MinionMemory Class
```python
class MinionMemory:
    @classmethod
    def init(cls, minion_id: str, chat_uid: str) -> 'MinionMemory'
    
    def save_voice(self, voice: 'MinionVoice') -> None
    
    def save_summary(self, summary: str) -> None
    
    def get_summaries(self) -> List[str]
    
    def get_voice_info(self) -> Dict
```

## Mock Interfaces

### RedisDatabase Mock (for Xavier's implementation)
```python
class RedisDatabase:
    def write(self, key: str, value: Any) -> None
    def read(self, key: str) -> Any
    def delete(self, key: str) -> None
    def exists(self, key: str) -> bool
```

### CursorChat Mock (for Marcus's implementation)
```python
@dataclass
class ChatMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime

@dataclass  
class CursorChat:
    chat_uid: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
```

## Dependencies

```
openai>=1.0.0
httpx>=0.25.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.0.0
```

## Notes
- All API clients will use async/await for I/O operations
- Configuration will be loaded from environment variables and YAML files
- Comprehensive error handling and logging throughout
- Type hints on all public interfaces

