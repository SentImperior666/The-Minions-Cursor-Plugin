"""
Tests for CodebaseIndexer.

Uses fakeredis and MockEmbeddingProvider for testing.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import fakeredis

from src.minions.database.redis_database import RedisDatabase
from src.minions.indexer.codebase_indexer import CodebaseIndexer
from src.minions.indexer.embeddings import MockEmbeddingProvider, cosine_similarity


class TestMockEmbeddingProvider:
    """Test suite for MockEmbeddingProvider."""
    
    def test_embed_returns_correct_dimension(self):
        """Test that embeddings have correct dimension."""
        provider = MockEmbeddingProvider(dimension=512)
        
        embedding = provider.embed("test text")
        
        assert len(embedding) == 512
    
    def test_embed_is_deterministic(self):
        """Test that same text produces same embedding."""
        provider = MockEmbeddingProvider()
        
        embedding1 = provider.embed("test text")
        embedding2 = provider.embed("test text")
        
        assert embedding1 == embedding2
    
    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        provider = MockEmbeddingProvider()
        
        embedding1 = provider.embed("text one")
        embedding2 = provider.embed("text two")
        
        assert embedding1 != embedding2
    
    def test_embed_batch(self):
        """Test batch embedding."""
        provider = MockEmbeddingProvider()
        
        embeddings = provider.embed_batch(["text1", "text2", "text3"])
        
        assert len(embeddings) == 3
        assert len(embeddings[0]) == provider.dimension


class TestCosineSimilarity:
    """Test suite for cosine_similarity function."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors is 1."""
        vec = [1.0, 0.0, 0.0]
        
        similarity = cosine_similarity(vec, vec)
        
        assert abs(similarity - 1.0) < 0.0001
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors is -1."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert abs(similarity - (-1.0)) < 0.0001
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors is 0."""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert abs(similarity) < 0.0001


class TestCodebaseIndexer:
    """Test suite for CodebaseIndexer."""
    
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
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create some test files
            (workspace / "main.py").write_text(
                "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()\n"
            )
            
            (workspace / "utils.py").write_text(
                "def helper():\n    return 42\n\ndef calculate(x, y):\n    return x + y\n"
            )
            
            # Create a subdirectory with files
            subdir = workspace / "lib"
            subdir.mkdir()
            (subdir / "module.py").write_text(
                "class MyClass:\n    def __init__(self):\n        self.value = 0\n"
            )
            
            # Create a .git directory (should be ignored)
            git_dir = workspace / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("git config")
            
            yield workspace
    
    @pytest.fixture
    def indexer(self, temp_workspace, db):
        """Create a CodebaseIndexer with test workspace."""
        return CodebaseIndexer(
            workspace_path=str(temp_workspace),
            redis_db=db,
            embedding_provider=MockEmbeddingProvider()
        )
    
    def test_get_files_to_index(self, indexer, temp_workspace):
        """Test file discovery."""
        files = indexer._get_files_to_index()
        
        # Should find Python files but not .git contents
        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "module.py" in file_names
        assert "config" not in file_names
    
    def test_should_ignore_git_directory(self, indexer, temp_workspace):
        """Test that .git directory is ignored."""
        git_path = Path(temp_workspace) / ".git"
        
        assert indexer._should_ignore_dir(git_path) is True
    
    def test_should_index_python_file(self, indexer, temp_workspace):
        """Test that Python files are indexed."""
        py_file = Path(temp_workspace) / "main.py"
        
        assert indexer._should_index_file(py_file) is True
    
    def test_split_into_chunks(self, indexer):
        """Test content splitting into chunks."""
        content = "\n".join([f"line {i}" for i in range(100)])
        
        chunks = indexer._split_into_chunks(content, "test.py")
        
        assert len(chunks) > 0
        # Each chunk should have (text, line_start, line_end)
        for chunk_text, line_start, line_end in chunks:
            assert isinstance(chunk_text, str)
            assert isinstance(line_start, int)
            assert isinstance(line_end, int)
            assert line_start <= line_end
    
    def test_index_codebase(self, indexer, temp_workspace):
        """Test full codebase indexing."""
        result = indexer.index()
        
        assert result is True
        
        # Check stats
        stats = indexer.get_stats()
        assert stats["indexed_files"] > 0
    
    def test_search(self, indexer):
        """Test semantic search."""
        # First index the codebase
        indexer.index()
        
        # Search for something
        results = indexer.search("print hello world", top_k=3)
        
        assert len(results) > 0
        assert all(hasattr(r, 'file_path') for r in results)
        assert all(hasattr(r, 'score') for r in results)
        # Results should be sorted by score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_update_file(self, indexer, temp_workspace):
        """Test updating a single file."""
        # Index first
        indexer.index()
        
        # Modify a file
        (Path(temp_workspace) / "main.py").write_text(
            "def main():\n    print('Updated content')\n"
        )
        
        # Update the file
        result = indexer.update("main.py")
        
        assert result is True
    
    def test_remove_file(self, indexer, temp_workspace):
        """Test removing a file from index."""
        # Index first
        indexer.index()
        
        # Remove a file
        result = indexer.remove("main.py")
        
        assert result is True
    
    def test_get_indexed_files(self, indexer):
        """Test getting list of indexed files."""
        indexer.index()
        
        files = indexer.get_indexed_files()
        
        assert len(files) > 0
        assert any("main.py" in f for f in files)
    
    def test_clear_index(self, indexer):
        """Test clearing the index."""
        indexer.index()
        
        result = indexer.clear_index()
        
        assert result is True
        
        stats = indexer.get_stats()
        assert stats["indexed_files"] == 0
        assert stats["total_chunks"] == 0
    
    def test_incremental_indexing(self, indexer):
        """Test that unchanged files are not re-indexed."""
        # Index first time
        indexer.index()
        stats1 = indexer.get_stats()
        
        # Index again - should skip unchanged files
        indexer.index()
        stats2 = indexer.get_stats()
        
        # Stats should be the same
        assert stats1["indexed_files"] == stats2["indexed_files"]
    
    def test_large_file_splitting(self, indexer, temp_workspace):
        """Test that large files are properly split into chunks."""
        # Create a larger file
        large_content = "\n".join([f"# Line {i}\ndef function_{i}():\n    pass\n" for i in range(200)])
        (Path(temp_workspace) / "large_file.py").write_text(large_content)
        
        indexer.index()
        
        # Search should find content from the file
        results = indexer.search("function definition", top_k=10)
        
        assert len(results) > 0


class TestCodebaseIndexerEdgeCases:
    """Test edge cases for CodebaseIndexer."""
    
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
    
    def test_empty_workspace(self, db):
        """Test indexing an empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = CodebaseIndexer(
                workspace_path=tmpdir,
                redis_db=db,
                embedding_provider=MockEmbeddingProvider()
            )
            
            result = indexer.index()
            
            assert result is True
            assert indexer.get_stats()["indexed_files"] == 0
    
    def test_empty_file(self, db):
        """Test indexing an empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "empty.py").write_text("")
            
            indexer = CodebaseIndexer(
                workspace_path=str(workspace),
                redis_db=db,
                embedding_provider=MockEmbeddingProvider()
            )
            
            result = indexer.index()
            
            assert result is True
    
    def test_binary_file_ignored(self, db):
        """Test that binary files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # Create a file with non-text extension
            (workspace / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n')
            
            indexer = CodebaseIndexer(
                workspace_path=str(workspace),
                redis_db=db,
                embedding_provider=MockEmbeddingProvider()
            )
            
            files = indexer._get_files_to_index()
            
            assert len(files) == 0
    
    def test_get_file_content(self, db):
        """Test getting file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "test.py").write_text("print('hello')")
            
            indexer = CodebaseIndexer(
                workspace_path=str(workspace),
                redis_db=db
            )
            
            content = indexer.get_file_content("test.py")
            
            assert content == "print('hello')"
    
    def test_get_nonexistent_file_content(self, db):
        """Test getting content of nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = CodebaseIndexer(
                workspace_path=tmpdir,
                redis_db=db
            )
            
            content = indexer.get_file_content("nonexistent.py")
            
            assert content is None
