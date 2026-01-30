# Minions - Cursor Plugin (Task 2: Core Components)

This is **Victor's** implementation of Task 2 for the Minions Cursor Plugin project.

## Overview

Task 2 implements the core Minion logic including:
- **Minion** - Main orchestration class
- **MinionAgent** - LLM agent for chat summarization and command processing
- **MinionVoice** - Voice synthesis using ElevenLabs
- **MinionMemory** - State persistence using Redis
- **API Clients** - OpenAI, ElevenLabs, and Twilio integrations

## Project Structure

```
vgh/
├── src/
│   └── minions/
│       ├── __init__.py
│       ├── minion.py           # Main Minion class
│       ├── agent.py            # MinionAgent - LLM summarization
│       ├── voice.py            # MinionVoice - ElevenLabs integration
│       ├── memory.py           # MinionMemory - State management
│       └── api/
│           ├── __init__.py
│           ├── openai_api.py   # OpenAI client
│           ├── elevenlabs_api.py # ElevenLabs client
│           └── twilio_api.py   # Twilio client
├── tests/
│   ├── test_minion.py
│   ├── test_agent.py
│   ├── test_voice.py
│   ├── test_memory.py
│   └── test_apis.py
├── mocks/
│   ├── redis_mock.py          # Mock for RedisDatabase (Xavier's task)
│   └── cursor_mock.py         # Mock for CursorChat (Marcus's task)
├── configs/
│   └── voice_config.yaml      # Voice configuration
├── requirements.txt
├── pytest.ini
└── README.md
```

## Dependencies

This task depends on components from other assistants:
- **Marcus (uwm)**: CursorListener, CursorDatabase, CursorChat
- **Xavier (xfw)**: RedisDatabase, CodebaseIndexer

Mock implementations are provided in the `mocks/` directory.

## Installation

```bash
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/ -v
```

## Environment Variables

Set these environment variables for production use:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_key

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_key

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+15551234567
```

## Usage

### Creating a Minion

```python
from src.minions import Minion

# Spawn a new minion (or load existing)
minion = Minion.spawn(chat_uid="cursor_chat_123")

# Get the current summary
summary = minion.get_summary()
print(summary)

# Process a voice command
result = minion.process_command("give me a status update")
print(result["response"])
```

### Making a Phone Call

```python
# Call the user with the summary
call = minion.call_user(
    phone_number="+15559876543",
    webhook_url="https://your-server.com/twiml",
)
print(f"Call initiated: {call.call_sid}")
```

### Voice Synthesis

```python
# Convert text to speech
audio = minion.speak("Hello! Here's your update.")

# The audio can be streamed to Twilio
```

## API Components

### MinionAgent

Handles chat summarization and command processing:
- `load_chat(chat_uid)` - Load chat from database
- `summarize_chat(chat)` - Generate summary using OpenAI
- `process_command(command)` - Handle voice commands (stop, forget, spawn, etc.)

### MinionVoice

Handles voice synthesis:
- `init(minion_id, name, config)` - Create a new voice
- `load(minion_id, voice_info)` - Load existing voice
- `text_to_speech(text)` - Convert text to audio
- `speech_to_text(audio)` - Transcribe audio

### MinionMemory

Handles state persistence:
- `init(minion_id, chat_uid)` - Initialize memory
- `save_voice(voice)` - Persist voice configuration
- `save_summary(summary)` - Store chat summary
- `get_summaries()` - Retrieve all summaries

## Coordination with Other Tasks

### Marcus (Task 1) provides:
- `CursorChat` data type with messages
- `ChatMessage` data type
- `CursorListener` for monitoring chats

### Xavier (Task 3) provides:
- `RedisDatabase` for persistence
- `CodebaseIndexer` for codebase queries

## License

MIT License
