"""
Codebase Indexer module.

Provides components for indexing the codebase to enable Q&A.
Wraps implementation from xfw workspace (Task 3 - Xavier).
"""

from .codebase_indexer import CodebaseIndexer
from .embeddings import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    MockEmbeddingProvider,
    cosine_similarity,
)

__all__ = [
    "CodebaseIndexer",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "MockEmbeddingProvider",
    "cosine_similarity",
]
