"""
CodebaseIndexer for The Minions Cursor Plugin.

This module provides semantic search capabilities over a codebase
by indexing files with embeddings and storing them in Redis.
"""

import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional, Set, Tuple

from ..database.redis_database import RedisDatabase
from ..database.data_types import SearchResult, IndexedFile, EmbeddingChunk
from .embeddings import EmbeddingProvider, MockEmbeddingProvider, cosine_similarity

logger = logging.getLogger(__name__)


# Default file extensions to index
DEFAULT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".h",
    ".rb", ".php", ".swift", ".kt", ".scala",
    ".md", ".txt", ".json", ".yaml", ".yml",
    ".html", ".css", ".scss", ".sql"
}

# Default directories to ignore
DEFAULT_IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".pytest_cache",
    "venv", ".venv", "env", ".env",
    "dist", "build", "target", "out",
    ".idea", ".vscode", ".cursor"
}

# Maximum file size to index (1MB)
MAX_FILE_SIZE = 1024 * 1024

# Chunk size for splitting files (in characters)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


class CodebaseIndexer:
    """
    Indexes a codebase for semantic search.
    
    The indexer:
    1. Scans the workspace for code files
    2. Splits files into chunks
    3. Generates embeddings for each chunk
    4. Stores embeddings in Redis
    5. Enables semantic search over the codebase
    
    Example usage:
        indexer = CodebaseIndexer(
            workspace_path="/path/to/project",
            redis_db=redis_db,
            embedding_provider=OpenAIEmbeddingProvider()
        )
        
        # Index the codebase
        indexer.index()
        
        # Search for relevant code
        results = indexer.search("how to authenticate users", top_k=5)
        for result in results:
            print(f"{result.file_path}: {result.score}")
    """
    
    def __init__(
        self,
        workspace_path: str,
        redis_db: RedisDatabase,
        embedding_provider: Optional[EmbeddingProvider] = None,
        extensions: Optional[Set[str]] = None,
        ignore_dirs: Optional[Set[str]] = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        """
        Initialize CodebaseIndexer.
        
        Args:
            workspace_path: Path to the workspace to index
            redis_db: RedisDatabase instance for storage
            embedding_provider: Provider for generating embeddings
            extensions: Set of file extensions to index
            ignore_dirs: Set of directory names to ignore
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.redis_db = redis_db
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Redis key prefixes
        self._index_prefix = "codebase:index:"
        self._chunk_prefix = "codebase:chunk:"
        self._embedding_prefix = "codebase:embedding:"
    
    def _get_file_hash(self, content: str) -> str:
        """Generate hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_path_hash(self, file_path: str) -> str:
        """Generate hash of file path for Redis key."""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed."""
        # Check extension
        if file_path.suffix.lower() not in self.extensions:
            return False
        
        # Check file size
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                logger.debug(f"Skipping large file: {file_path}")
                return False
        except OSError:
            return False
        
        return True
    
    def _should_ignore_dir(self, dir_path: Path) -> bool:
        """Check if a directory should be ignored."""
        return dir_path.name in self.ignore_dirs
    
    def _get_files_to_index(self) -> List[Path]:
        """Get list of files to index in the workspace."""
        files = []
        
        for root, dirs, filenames in os.walk(self.workspace_path):
            root_path = Path(root)
            
            # Filter out ignored directories (modifies dirs in-place)
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(root_path / d)]
            
            for filename in filenames:
                file_path = root_path / filename
                if self._should_index_file(file_path):
                    files.append(file_path)
        
        return files
    
    def _split_into_chunks(
        self,
        content: str,
        file_path: str
    ) -> List[Tuple[str, int, int]]:
        """
        Split content into overlapping chunks.
        
        Args:
            content: The file content
            file_path: Path to the file (for context)
            
        Returns:
            List of (chunk_text, line_start, line_end) tuples
        """
        lines = content.split('\n')
        chunks = []
        
        if not lines:
            return chunks
        
        # Build chunks by lines
        current_chunk_lines = []
        current_chunk_chars = 0
        chunk_start_line = 0
        
        for i, line in enumerate(lines):
            line_with_newline = line + '\n'
            line_len = len(line_with_newline)
            
            if current_chunk_chars + line_len > self.chunk_size and current_chunk_lines:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk_lines)
                chunks.append((chunk_text, chunk_start_line + 1, i))
                
                # Calculate overlap (number of lines to keep)
                overlap_chars = 0
                overlap_lines = []
                for line_content in reversed(current_chunk_lines):
                    overlap_chars += len(line_content) + 1
                    overlap_lines.insert(0, line_content)
                    if overlap_chars >= self.chunk_overlap:
                        break
                
                # Start new chunk with overlap
                current_chunk_lines = overlap_lines
                current_chunk_chars = overlap_chars
                chunk_start_line = i - len(overlap_lines)
            
            current_chunk_lines.append(line)
            current_chunk_chars += line_len
        
        # Add final chunk if there's remaining content
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append((chunk_text, chunk_start_line + 1, len(lines)))
        
        return chunks
    
    def _index_file(self, file_path: Path) -> bool:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file to index
            
        Returns:
            True if indexing successful, False otherwise
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            content_hash = self._get_file_hash(content)
            
            # Relative path for storage
            rel_path = str(file_path.relative_to(self.workspace_path))
            path_hash = self._get_path_hash(rel_path)
            
            # Check if file needs re-indexing
            index_key = f"{self._index_prefix}{path_hash}"
            existing_data = self.redis_db.read(index_key)
            
            if existing_data:
                existing_index = IndexedFile.from_dict(existing_data)
                if existing_index.content_hash == content_hash:
                    logger.debug(f"Skipping unchanged file: {rel_path}")
                    return True
                else:
                    # Remove old chunks
                    self._remove_file_chunks(existing_index.chunk_ids)
            
            # Split into chunks
            chunks = self._split_into_chunks(content, rel_path)
            
            if not chunks:
                logger.debug(f"No chunks generated for: {rel_path}")
                return True
            
            # Generate embeddings for all chunks
            chunk_texts = [c[0] for c in chunks]
            embeddings = self.embedding_provider.embed_batch(chunk_texts)
            
            # Store chunks and embeddings
            chunk_ids = []
            for i, ((chunk_text, line_start, line_end), embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                
                chunk = EmbeddingChunk(
                    chunk_id=chunk_id,
                    file_path=rel_path,
                    content=chunk_text,
                    embedding=embedding,
                    line_start=line_start,
                    line_end=line_end
                )
                
                chunk_key = f"{self._chunk_prefix}{chunk_id}"
                self.redis_db.write(chunk_key, chunk.to_dict())
            
            # Store file index
            indexed_file = IndexedFile(
                file_path=rel_path,
                content_hash=content_hash,
                chunk_ids=chunk_ids
            )
            self.redis_db.write(index_key, indexed_file.to_dict())
            
            logger.info(f"Indexed {rel_path} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
            return False
    
    def _remove_file_chunks(self, chunk_ids: List[str]) -> None:
        """Remove chunks from Redis."""
        for chunk_id in chunk_ids:
            chunk_key = f"{self._chunk_prefix}{chunk_id}"
            self.redis_db.delete(chunk_key)
    
    def index(self) -> bool:
        """
        Index the entire codebase.
        
        Returns:
            True if indexing successful, False otherwise
        """
        logger.info(f"Starting indexing of {self.workspace_path}")
        
        files = self._get_files_to_index()
        logger.info(f"Found {len(files)} files to index")
        
        success_count = 0
        for file_path in files:
            if self._index_file(file_path):
                success_count += 1
        
        logger.info(f"Indexed {success_count}/{len(files)} files successfully")
        return success_count == len(files)
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for relevant code chunks.
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.embedding_provider.embed(query)
        
        # Get all chunk keys
        chunk_keys = self.redis_db.keys(f"{self._chunk_prefix}*")
        
        # Calculate similarities
        results = []
        for chunk_key in chunk_keys:
            chunk_data = self.redis_db.read(chunk_key)
            if not chunk_data:
                continue
            
            chunk = EmbeddingChunk.from_dict(chunk_data)
            similarity = cosine_similarity(query_embedding, chunk.embedding)
            
            results.append(SearchResult(
                file_path=chunk.file_path,
                content=chunk.content,
                score=similarity,
                line_start=chunk.line_start,
                line_end=chunk.line_end
            ))
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def update(self, file_path: str) -> bool:
        """
        Update index for a specific file.
        
        Args:
            file_path: Path to the file to update
            
        Returns:
            True if update successful, False otherwise
        """
        full_path = self.workspace_path / file_path
        if not full_path.exists():
            return self.remove(file_path)
        
        return self._index_file(full_path)
    
    def remove(self, file_path: str) -> bool:
        """
        Remove a file from the index.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        path_hash = self._get_path_hash(file_path)
        index_key = f"{self._index_prefix}{path_hash}"
        
        existing_data = self.redis_db.read(index_key)
        if not existing_data:
            return True
        
        existing_index = IndexedFile.from_dict(existing_data)
        self._remove_file_chunks(existing_index.chunk_ids)
        self.redis_db.delete(index_key)
        
        logger.info(f"Removed {file_path} from index")
        return True
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """
        Get content of an indexed file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content if found, None otherwise
        """
        full_path = self.workspace_path / file_path
        try:
            return full_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
    
    def get_indexed_files(self) -> List[str]:
        """
        Get list of all indexed files.
        
        Returns:
            List of file paths
        """
        index_keys = self.redis_db.keys(f"{self._index_prefix}*")
        files = []
        
        for key in index_keys:
            data = self.redis_db.read(key)
            if data:
                indexed_file = IndexedFile.from_dict(data)
                files.append(indexed_file.file_path)
        
        return files
    
    def clear_index(self) -> bool:
        """
        Clear the entire index.
        
        Returns:
            True if clear successful, False otherwise
        """
        # Remove all chunks
        chunk_keys = self.redis_db.keys(f"{self._chunk_prefix}*")
        for key in chunk_keys:
            self.redis_db.delete(key)
        
        # Remove all index entries
        index_keys = self.redis_db.keys(f"{self._index_prefix}*")
        for key in index_keys:
            self.redis_db.delete(key)
        
        logger.info("Cleared codebase index")
        return True
    
    def get_stats(self) -> dict:
        """
        Get indexing statistics.
        
        Returns:
            Dictionary with stats
        """
        index_keys = self.redis_db.keys(f"{self._index_prefix}*")
        chunk_keys = self.redis_db.keys(f"{self._chunk_prefix}*")
        
        return {
            "indexed_files": len(index_keys),
            "total_chunks": len(chunk_keys),
            "workspace_path": str(self.workspace_path)
        }
