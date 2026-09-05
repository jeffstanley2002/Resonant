from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, max_size: int = 128, ttl_seconds: int = 900) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._values: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        item = self._values.get(key)
        if item is None:
            return None
        created_at, value = item
        if now - created_at > self.ttl_seconds:
            self._values.pop(key, None)
            return None
        self._values.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        self._values[key] = (time.monotonic(), value)
        self._values.move_to_end(key)
        while len(self._values) > self.max_size:
            self._values.popitem(last=False)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> tuple[T, bool]:
        cached = self.get(key)
        if cached is not None:
            return cached, True
        value = factory()
        self.set(key, value)
        return value, False

    def clear(self) -> None:
        self._values.clear()
