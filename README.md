# The Minions Cursor Plugin 🍌

An LLM agent that monitors your Cursor IDE chats, summarizes conversations, and calls you on the phone to tell you about them — just like the lovable Minions from Despicable Me!

## Features

- **Chat Monitoring**: Automatically monitors all your Cursor IDE chat sessions
- **Smart Summarization**: Uses AI to create concise summaries of your coding conversations  
- **Voice Calls**: Calls you on your phone to deliver summaries using custom AI-generated voices
- **Voice Commands**: Control minions with voice commands like "stop", "forget", "spawn"
- **Codebase Q&A**: Ask questions about your codebase during calls

## Quick Start

### Prerequisites

- Python 3.8+
- Cursor IDE
- Redis server (optional, uses in-memory fallback)
- API keys for:
  - OpenAI (for summarization)
  - ElevenLabs (for voice synthesis)
  - Twilio (for phone calls)

### Installation

```bash
# Clone the repository
git clone https://github.com/minions/cursor-plugin.git
cd cursor-plugin

# Install dependencies
pip install -r requirements.txt

# Or install with optional dependencies
pip install -e ".[full]"
```

### Configuration

Set up your API keys as environment variables:

```bash
export OPENAI_API_KEY="your-openai-key"
export ELEVEN_API_KEY="your-elevenlabs-key"
export TWILIO_ACCOUNT_SID="your-twilio-sid"
export TWILIO_AUTH_TOKEN="your-twilio-token"
export TWILIO_FROM_NUMBER="+1234567890"
```

Or create a `.env` file in the project root.

### Usage

```bash
# Start monitoring Cursor chats
minions start

# List available Cursor chats
minions chats

# Spawn a minion for a specific chat
minions spawn <chat_uid>

# Check status of all minions
minions status
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    The Minions Cursor Plugin                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐   │
│  │   Cursor    │────▶│   Cursor     │────▶│    Minion      │   │
│  │   IDE       │     │   Listener   │     │    Manager     │   │
│  └─────────────┘     └──────────────┘     └───────┬────────┘   │
│                                                    │            │
│                      ┌────────────────────────────┼───────┐    │
│                      │           Minion           ▼       │    │
│                      │  ┌─────────┐ ┌──────────┐ ┌─────┐  │    │
│                      │  │  Agent  │ │  Voice   │ │Memory│  │    │
│                      │  └────┬────┘ └────┬─────┘ └──┬──┘  │    │
│                      └───────┼──────────┼──────────┼──────┘    │
│                              │          │          │           │
│  ┌───────────────────────────┴──────────┴──────────┴────────┐  │
│  │                       External APIs                       │  │
│  │  ┌────────┐   ┌────────────┐   ┌────────┐   ┌─────────┐  │  │
│  │  │ OpenAI │   │ ElevenLabs │   │ Twilio │   │  Redis  │  │  │
│  │  └────────┘   └────────────┘   └────────┘   └─────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Description |
|-----------|-------------|
| **CursorDatabase** | Reads Cursor's local SQLite database |
| **CursorListener** | Monitors chats for new messages |
| **Minion** | Main orchestration class |
| **MinionAgent** | LLM agent for summarization |
| **MinionVoice** | Voice synthesis via ElevenLabs |
| **MinionMemory** | Persistent storage via Redis |
| **RedisDatabase** | Local Redis interface |

## Voice Commands

During a phone call, you can say:

- **"Stop"** - Stop monitoring the current chat
- **"Forget"** - Clear the minion's memory
- **"Spawn"** - Create a new minion
- **Questions** - Ask anything about your code or conversation

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with Docker
docker-compose up test

# Build executable
python build.py
```

## Building Executables

### Windows

```bash
pip install pyinstaller
python build.py
# Output: dist/minions.exe
```

### Linux

```bash
pip install pyinstaller
python build.py
# Output: dist/minions

# For AppImage (requires appimagetool)
python build.py --appimage
```

## Project Structure

```
├── src/
│   └── minions/
│       ├── __init__.py      # Package exports
│       ├── core.py          # Minion and MinionManager
│       ├── agent.py         # MinionAgent
│       ├── voice.py         # MinionVoice
│       ├── memory.py        # MinionMemory
│       ├── cli.py           # Command-line interface
│       ├── cursor/          # Cursor integration
│       ├── database/        # Redis interface
│       └── api/             # External API wrappers
├── configs/                 # Configuration files
├── tests/                   # Test suite
├── requirements.txt         # Dependencies
├── pyproject.toml          # Project metadata
└── build.py                # Build script
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.

---

*"Bello!"* 🍌
