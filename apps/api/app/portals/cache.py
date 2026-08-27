"""A small in-memory TTL cache with single-flight de-duplication.

Single-flight matters here specifically because one portal endpoint often
backs several different tool calls (e.g. NPP's getBMapData backs stations,
projects, and region lookups) — without it, N concurrent tool calls before
the first response lands would each trigger their own fetch of a
multi-hundred-KB payload.

In-memory rather than on-disk: total resident portal data is expected to
stay well under a few MB (see app/portals/npp/client.py), so there's no
real benefit to persisting it across process restarts, and it avoids a new
class of "stale file on disk" bugs.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class _Entry[T]:
    value: T
    expires_at: float


class TTLCache[T]:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry[T]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def get_or_fetch(self, key: str, ttl_seconds: float, fetch: Callable[[], Awaitable[T]]) -> T:
        entry = self._entries.get(key)
        now = time.monotonic()
        if entry is not None and entry.expires_at > now:
            return entry.value

        # Single-flight: only one concurrent caller for a given key actually
        # fetches; the rest wait on the same lock and then read the cache
        # the first caller just populated.
        async with self._lock_for(key):
            entry = self._entries.get(key)
            now = time.monotonic()
            if entry is not None and entry.expires_at > now:
                return entry.value

            value = await fetch()
            self._entries[key] = _Entry(value=value, expires_at=time.monotonic() + ttl_seconds)
            return value

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)
