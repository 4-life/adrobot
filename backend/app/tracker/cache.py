"""A small in-memory TTL cache for Keitaro lists (offers, domains, groups, sources)."""

import time
from collections.abc import Awaitable, Callable
from typing import cast

LOOKUP_TTL_SECONDS = 60.0


class TtlCache:
    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl
        self._clock = clock
        self._items: dict[str, tuple[float, object]] = {}

    async def get[T](self, key: str, load: Callable[[], Awaitable[T]]) -> T:
        now = self._clock()
        cached = self._items.get(key)
        if cached is not None and now - cached[0] < self._ttl:
            return cast(T, cached[1])
        value = await load()
        self._items[key] = (now, value)
        return value

    def clear(self) -> None:
        self._items.clear()


lookups = TtlCache(LOOKUP_TTL_SECONDS)
