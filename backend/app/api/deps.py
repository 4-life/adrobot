from collections.abc import AsyncIterator

from app.tracker.factory import create_tracker
from app.tracker.port import TrackerProvider


async def get_tracker() -> AsyncIterator[TrackerProvider]:
    """The configured tracker adapter per request (its errors answer 502: app/api/errors.py)."""
    async with create_tracker() as tracker:
        yield tracker
