"""
Embedding providers for CodebaseIndexer.

This module provides interfaces and implementations for generating
text embeddings using various providers (OpenAI, etc.).
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-small model.
    
    This provider uses OpenAI's embedding API to generate embeddings
    for text. It's used by CodebaseIndexer for semantic search.
    """
    
    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSION = 1536
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: Model to use for embeddings
            dimension: Dimension of embeddings
        """
        self.api_key = api_key
        self.model = model
        self._dimension = dimension
        self._client = None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        return self._client
    
    @property
    def dimension(self) -> int:
        """Return the dimension of embeddings."""
        return self._dimension
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using OpenAI API.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding
        """
        client = self._get_client()
        try:
            response = client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self._dimension
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        client = self._get_client()
        try:
            response = client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self._dimension
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing.
    
    Generates deterministic embeddings based on text hash.
    Useful for testing without API calls.
    """
    
    def __init__(self, dimension: int = 1536):
        """
        Initialize mock embedding provider.
        
        Args:
            dimension: Dimension of embeddings
        """
        self._dimension = dimension
    
    @property
    def dimension(self) -> int:
        """Return the dimension of embeddings."""
        return self._dimension
    
    def _hash_to_embedding(self, text: str) -> List[float]:
        """Generate deterministic embedding from text hash."""
        # Create a hash of the text
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Use the hash as a seed for reproducible random numbers
        seed = int.from_bytes(hash_bytes[:4], 'big')
        rng = np.random.RandomState(seed)
        
        # Generate embedding and normalize
        embedding = rng.randn(self._dimension).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
    
    def embed(self, text: str) -> List[float]:
        """
        Generate mock embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding
        """
        return self._hash_to_embedding(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate mock embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        return [self._hash_to_embedding(text) for text in texts]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine similarity score
    """
    a_np = np.array(a)
    b_np = np.array(b)
    
    dot_product = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))
