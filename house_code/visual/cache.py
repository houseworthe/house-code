"""
LRU cache for visual memory with disk persistence.

Caches VisualMemory entries to avoid redundant compression.
Evicts based on LRU policy and size limits.
"""

import json
import os
from collections import OrderedDict
from typing import Optional, Dict, List
from datetime import datetime

from .models import VisualMemory, VisualTokens


class VisualCache:
    """
    LRU cache for visual memory entries.

    Features:
    - LRU eviction policy
    - Size-based eviction (max MB)
    - Count-based eviction (max entries)
    - Disk persistence
    - Cache statistics
    """

    def __init__(
        self,
        max_entries: int = 50,
        max_size_mb: int = 100,
        cache_path: Optional[str] = None
    ):
        """
        Initialize visual cache.

        Args:
            max_entries: Maximum number of entries before eviction
            max_size_mb: Maximum cache size in MB before eviction
            cache_path: Path to persistence file (optional)
        """
        self.max_entries = max_entries
        self.max_size_mb = max_size_mb
        self.cache_path = cache_path

        # OrderedDict for LRU: most recently used at end
        self.cache: OrderedDict[str, VisualMemory] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[VisualMemory]:
        """
        Retrieve entry from cache.

        Updates LRU order on access.

        Args:
            key: Cache key

        Returns:
            VisualMemory if found, None otherwise
        """
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        return None

    def put(self, key: str, value: VisualMemory):
        """
        Add entry to cache.

        Evicts oldest entries if limits exceeded.

        Args:
            key: Cache key
            value: VisualMemory to cache
        """
        # Remove if already exists (will re-add at end)
        if key in self.cache:
            del self.cache[key]

        # Add to end (most recently used)
        self.cache[key] = value

        # Evict if over limits
        self._evict_if_needed()

    def remove(self, key: str) -> bool:
        """
        Remove entry from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if removed, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        """Clear all entries from cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def size_mb(self) -> float:
        """
        Calculate current cache size in MB.

        Returns:
            Size in megabytes
        """
        total_bytes = 0

        for memory in self.cache.values():
            # Count visual tokens (rough estimate: 8 bytes per token)
            total_bytes += len(memory.visual_tokens) * 8

            # Count original text length
            total_bytes += memory.original_text_length

        return total_bytes / (1024 * 1024)

    def stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "entries": len(self.cache),
            "max_entries": self.max_entries,
            "size_mb": round(self.size_mb(), 2),
            "max_size_mb": self.max_size_mb,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 1),
            "evictions": self.evictions,
        }

    def keys(self) -> List[str]:
        """
        Get all cache keys.

        Returns:
            List of keys in LRU order (oldest first)
        """
        return list(self.cache.keys())

    def save(self, path: Optional[str] = None) -> bool:
        """
        Persist cache to disk.

        Args:
            path: Path to save to (uses self.cache_path if None)

        Returns:
            True if saved successfully
        """
        save_path = path or self.cache_path

        if not save_path:
            return False

        try:
            # Expand path
            save_path = os.path.expanduser(save_path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Serialize cache
            data = {
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
                "entries": {},
                "stats": {
                    "hits": self.hits,
                    "misses": self.misses,
                    "evictions": self.evictions,
                }
            }

            # Serialize each entry
            for key, memory in self.cache.items():
                data["entries"][key] = _serialize_visual_memory(memory)

            # Write to file
            with open(save_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True

        except (IOError, OSError) as e:
            print(f"Error saving cache: {e}")
            return False

    def load(self, path: Optional[str] = None) -> bool:
        """
        Load cache from disk.

        Args:
            path: Path to load from (uses self.cache_path if None)

        Returns:
            True if loaded successfully
        """
        load_path = path or self.cache_path

        if not load_path:
            return False

        try:
            # Expand path
            load_path = os.path.expanduser(load_path)

            if not os.path.exists(load_path):
                return False

            # Load from file
            with open(load_path, 'r') as f:
                data = json.load(f)

            # Clear current cache
            self.cache.clear()

            # Restore entries (maintains order from JSON)
            entries = data.get("entries", {})
            for key, entry_data in entries.items():
                memory = _deserialize_visual_memory(entry_data)
                self.cache[key] = memory

            # Restore stats
            stats = data.get("stats", {})
            self.hits = stats.get("hits", 0)
            self.misses = stats.get("misses", 0)
            self.evictions = stats.get("evictions", 0)

            return True

        except (IOError, OSError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading cache: {e}")
            return False

    def _evict_if_needed(self):
        """Evict oldest entries if limits exceeded."""
        # Evict by count
        while len(self.cache) > self.max_entries:
            # Remove oldest (first item)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1

        # Evict by size
        while self.size_mb() > self.max_size_mb and len(self.cache) > 0:
            # Remove oldest (first item)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1


def _serialize_visual_memory(memory: VisualMemory) -> dict:
    """
    Serialize VisualMemory to JSON-compatible dict.

    Args:
        memory: VisualMemory to serialize

    Returns:
        Dictionary representation
    """
    return {
        "message_ids": memory.message_ids,
        "visual_tokens": {
            "data": memory.visual_tokens.data,
            "metadata": memory.visual_tokens.metadata,
            "created_at": memory.visual_tokens.created_at,
        },
        "original_text_length": memory.original_text_length,
        "compression_ratio": memory.compression_ratio,
        "created_at": memory.created_at,
        "metadata": memory.metadata,
    }


def _deserialize_visual_memory(data: dict) -> VisualMemory:
    """
    Deserialize VisualMemory from dict.

    Args:
        data: Dictionary representation

    Returns:
        VisualMemory instance
    """
    visual_tokens_data = data["visual_tokens"]

    visual_tokens = VisualTokens(
        data=visual_tokens_data["data"],
        metadata=visual_tokens_data["metadata"],
        created_at=visual_tokens_data["created_at"],
    )

    return VisualMemory(
        message_ids=data["message_ids"],
        visual_tokens=visual_tokens,
        original_text_length=data["original_text_length"],
        compression_ratio=data["compression_ratio"],
        created_at=data["created_at"],
        metadata=data.get("metadata", {}),
    )
