# Xavier's Implementation Plan - Task 3

## Overview
Implementing the Redis Database Interface and CodebaseIndexer components for The Minions Cursor Plugin.

## Components to Implement

### 1. RedisDatabase
Local Redis database interface with the following operations:

```python
class RedisDatabase:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0)
    def connect(self) -> bool
    def disconnect(self) -> None
    def write(self, key: str, value: Any) -> bool
    def read(self, key: str) -> Optional[Any]
    def delete(self, key: str) -> bool
    def exists(self, key: str) -> bool
    def keys(self, pattern: str = "*") -> List[str]
    def flush(self) -> bool
```

**Data structures to support:**
- Minion info: `minion:{minion_id}` -> JSON with minion_id, chat_uid, minion_name
- Voice data: `minion:{minion_id}:voice` -> JSON with voice_name, voice_desc, voice_11labs_id
- Summaries: `minion:{minion_id}:summaries` -> List of summary strings
- Chat messages: `chat:{chat_uid}:messages` -> List of chat messages

### 2. CodebaseIndexer
Component that indexes the codebase for semantic search:

```python
class CodebaseIndexer:
    def __init__(self, workspace_path: str, redis_db: RedisDatabase)
    def index(self) -> bool
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]
    def update(self, file_path: str) -> bool
    def remove(self, file_path: str) -> bool
    def get_file_content(self, file_path: str) -> Optional[str]
```

**Features:**
- Index files with embeddings (using OpenAI embeddings API)
- Store embeddings in Redis
- Semantic search over codebase
- Incremental updates

### 3. Data Types

```python
@dataclass
class MinionInfo:
    minion_id: str
    chat_uid: str
    minion_name: str
    created_at: datetime

@dataclass
class VoiceData:
    voice_name: str
    voice_description: str
    elevenlabs_voice_id: str

@dataclass  
class SearchResult:
    file_path: str
    content: str
    score: float
    line_start: int
    line_end: int

@dataclass
class IndexedFile:
    file_path: str
    content_hash: str
    embedding: List[float]
    indexed_at: datetime
```

## Directory Structure

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

## Dependencies

### Production
- redis>=4.5.0
- openai>=1.0.0
- numpy>=1.24.0

### Development
- pytest>=7.0.0
- pytest-asyncio>=0.21.0
- fakeredis>=2.0.0

## Mock Interfaces for Other Assistants

I will provide clear interfaces that MinionMemory and CursorListener can use:

```python
# Interface for MinionMemory (Marcus/Victor to use)
class RedisDatabase:
    def write(self, key: str, value: Any) -> bool: ...
    def read(self, key: str) -> Optional[Any]: ...
```

## Testing Strategy

1. Unit tests with fakeredis (no real Redis needed)
2. Integration tests with Docker Redis
3. Test coverage target: >90%

## Implementation Order

1. Create project structure and dependencies
2. Implement RedisDatabase base class
3. Implement data types
4. Write RedisDatabase tests
5. Implement CodebaseIndexer
6. Implement embeddings module
7. Write CodebaseIndexer tests
8. Create Docker setup for testing

## Notes

- Will use fakeredis for testing to avoid dependency on running Redis
- Embeddings will be cached in Redis to avoid repeated API calls
- CodebaseIndexer will support incremental indexing based on file hashes
