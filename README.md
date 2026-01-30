# The Minions Cursor Plugin - Task 3

## Redis Database Interface and CodebaseIndexer

This module provides the storage and indexing layer for The Minions Cursor Plugin.

### Components

#### RedisDatabase

A clean interface for storing and retrieving data from a local Redis database.

**Features:**
- Basic CRUD operations (read, write, delete, exists)
- List operations for storing summaries and messages
- High-level operations for minion data, voice data, chat messages
- Abstract interface for easy mocking in tests

**Key Methods:**
```python
from src.minions.database import RedisDatabase, MinionInfo, VoiceData

db = RedisDatabase(host="localhost", port=6379)
db.connect()

# Save minion info
info = MinionInfo(minion_id="123", chat_uid="456", minion_name="Bob")
db.save_minion_info(info)

# Save voice data
voice = VoiceData(voice_name="Bob", voice_description="Friendly", elevenlabs_voice_id="el_123")
db.save_voice_data("123", voice)

# Add summaries
db.add_summary("123", "User asked about authentication")

# Add chat messages
msg = ChatMessageData(role="user", content="Hello")
db.add_chat_message("456", msg)

db.disconnect()
```

#### CodebaseIndexer

Semantic search over a codebase using embeddings.

**Features:**
- Indexes code files with OpenAI embeddings
- Stores embeddings in Redis
- Semantic search for relevant code
- Incremental updates (only re-indexes changed files)
- Configurable file extensions and ignore patterns

**Key Methods:**
```python
from src.minions.indexer import CodebaseIndexer, OpenAIEmbeddingProvider

indexer = CodebaseIndexer(
    workspace_path="/path/to/project",
    redis_db=db,
    embedding_provider=OpenAIEmbeddingProvider()
)

# Index the codebase
indexer.index()

# Search for relevant code
results = indexer.search("how to authenticate users", top_k=5)
for result in results:
    print(f"{result.file_path} (score: {result.score:.2f})")
    print(result.content)
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Running Tests

**Using pytest directly:**
```bash
pytest -v tests/
```

**Using Docker Compose:**
```bash
# Run tests with Redis
docker-compose up test

# Start development environment
docker-compose up -d redis
docker-compose run dev
```

### Project Structure

```
xfw/
├── src/
│   └── minions/
│       ├── __init__.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── redis_database.py
│       │   └── data_types.py
│       └── indexer/
│           ├── __init__.py
│           ├── codebase_indexer.py
│           └── embeddings.py
├── tests/
│   ├── __init__.py
│   ├── test_redis_database.py
│   └── test_codebase_indexer.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Interfaces for Other Tasks

#### For Task 1 (CursorListener):
```python
# Store chat messages
db.add_chat_message(chat_uid, ChatMessageData(role, content))

# Get all chat messages
messages = db.get_chat_messages(chat_uid)
```

#### For Task 2 (MinionMemory):
```python
# Store minion info
db.save_minion_info(MinionInfo(...))
db.save_voice_data(minion_id, VoiceData(...))

# Store/retrieve summaries
db.add_summary(minion_id, summary_text)
summaries = db.get_summaries(minion_id)
db.clear_summaries(minion_id)

# Get minion data
info = db.get_minion_info(minion_id)
voice = db.get_voice_data(minion_id)
```

### Data Types

- `MinionInfo`: minion_id, chat_uid, minion_name, created_at
- `VoiceData`: voice_name, voice_description, elevenlabs_voice_id
- `ChatMessageData`: role, content, timestamp, message_id
- `SearchResult`: file_path, content, score, line_start, line_end
- `IndexedFile`: file_path, content_hash, chunk_ids, indexed_at
- `EmbeddingChunk`: chunk_id, file_path, content, embedding, line_start, line_end

### Environment Variables

- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `OPENAI_API_KEY`: OpenAI API key for embeddings

---

**Task 3 by Xavier (xfw workspace)**
