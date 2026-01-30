"""
Mock implementation of RedisDatabase.

This is a placeholder for Xavier's Task 3 implementation.
The actual implementation will be in the xfw workspace.

This mock uses an in-memory dictionary to simulate Redis operations.
"""

from typing import Any, Dict, Optional
import json


class RedisDatabase:
    """
    Mock Redis database interface.
    
    This class provides a simple in-memory key-value store that mimics
    the Redis interface that Xavier will implement in Task 3.
    
    The actual implementation should connect to a local Redis instance.
    """
    
    _instance: Optional['RedisDatabase'] = None
    _store: Dict[str, str] = {}
    
    def __new__(cls) -> 'RedisDatabase':
        """Singleton pattern to ensure single database instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._store = {}
        return cls._instance
    
    def write(self, key: str, value: Any) -> None:
        """
        Write a value to the database.
        
        Args:
            key: The key to store the value under
            value: The value to store (will be JSON serialized)
        """
        if isinstance(value, (dict, list)):
            self._store[key] = json.dumps(value)
        else:
            self._store[key] = str(value)
    
    def read(self, key: str) -> Optional[Any]:
        """
        Read a value from the database.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored value, or None if key doesn't exist
        """
        value = self._store.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the database.
        
        Args:
            key: The key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the database.
        
        Args:
            key: The key to check
            
        Returns:
            True if key exists, False otherwise
        """
        return key in self._store
    
    def clear(self) -> None:
        """Clear all data from the mock database. Useful for testing."""
        self._store.clear()
    
    def list_append(self, key: str, value: Any) -> None:
        """
        Append a value to a list stored at key.
        
        Args:
            key: The key storing the list
            value: The value to append
        """
        existing = self.read(key)
        if existing is None:
            existing = []
        elif not isinstance(existing, list):
            existing = [existing]
        existing.append(value)
        self.write(key, existing)
    
    def list_get(self, key: str) -> list:
        """
        Get all values from a list stored at key.
        
        Args:
            key: The key storing the list
            
        Returns:
            The list, or empty list if key doesn't exist
        """
        value = self.read(key)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
