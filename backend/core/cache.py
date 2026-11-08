"""Tiny in-process LRU cache for repeated analyses of identical code."""

import hashlib
from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


def cache_key(*parts: object) -> str:
    """Stable SHA-256 key from arbitrary parts."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(repr(part).encode())
        digest.update(b"\x00")
    return digest.hexdigest()


class LRUCache(Generic[T]):
    """Bounded mapping that evicts the least recently used entry."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        self._data: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> T | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: str, value: T) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
