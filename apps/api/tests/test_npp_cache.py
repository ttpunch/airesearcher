"""Tests for the generic TTLCache (app/portals/cache.py) in isolation —
no HTTP, no NPP-specific logic. See test_npp_client.py for the same
behaviors exercised through NppClient.
"""

import asyncio

from app.portals.cache import TTLCache


async def test_cache_hit_avoids_refetch():
    cache = TTLCache[int]()
    calls = 0

    async def fetch() -> int:
        nonlocal calls
        calls += 1
        return 42

    first = await cache.get_or_fetch("key", 60.0, fetch)
    second = await cache.get_or_fetch("key", 60.0, fetch)
    assert first == second == 42
    assert calls == 1


async def test_expired_entry_refetches():
    cache = TTLCache[int]()
    calls = 0

    async def fetch() -> int:
        nonlocal calls
        calls += 1
        return calls

    first = await cache.get_or_fetch("key", 0.01, fetch)
    await asyncio.sleep(0.05)
    second = await cache.get_or_fetch("key", 0.01, fetch)
    assert first == 1
    assert second == 2
    assert calls == 2


async def test_single_flight_dedupes_concurrent_fetches():
    cache = TTLCache[int]()
    calls = 0

    async def slow_fetch() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return calls

    results = await asyncio.gather(
        cache.get_or_fetch("key", 60.0, slow_fetch),
        cache.get_or_fetch("key", 60.0, slow_fetch),
        cache.get_or_fetch("key", 60.0, slow_fetch),
    )
    assert calls == 1
    assert results == [1, 1, 1]


async def test_different_keys_fetch_independently():
    cache = TTLCache[int]()
    calls = 0

    async def fetch() -> int:
        nonlocal calls
        calls += 1
        return calls

    a = await cache.get_or_fetch("a", 60.0, fetch)
    b = await cache.get_or_fetch("b", 60.0, fetch)
    assert (a, b) == (1, 2)
    assert calls == 2


async def test_invalidate_forces_refetch():
    cache = TTLCache[int]()
    calls = 0

    async def fetch() -> int:
        nonlocal calls
        calls += 1
        return calls

    await cache.get_or_fetch("key", 60.0, fetch)
    cache.invalidate("key")
    second = await cache.get_or_fetch("key", 60.0, fetch)
    assert second == 2
    assert calls == 2
