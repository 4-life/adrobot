from app.tracker.cache import TtlCache


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_value_is_reused_until_the_ttl_passes() -> None:
    clock = Clock()
    cache = TtlCache(60, clock=clock)
    loads = 0

    async def load() -> int:
        nonlocal loads
        loads += 1
        return loads

    assert await cache.get("offers", load) == 1
    clock.now = 59
    assert await cache.get("offers", load) == 1
    clock.now = 60
    assert await cache.get("offers", load) == 2
