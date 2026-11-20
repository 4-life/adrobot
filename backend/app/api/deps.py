from collections.abc import AsyncIterator

from fastapi import HTTPException

from app.tracker.factory import create_tracker
from app.tracker.port import TrackerError, TrackerProvider


async def get_tracker() -> AsyncIterator[TrackerProvider]:
    """The configured tracker adapter per request; its errors answer 502 with its message."""
    async with create_tracker() as tracker:
        try:
            yield tracker
        except TrackerError as error:
            raise HTTPException(status_code=502, detail=error.message) from error
