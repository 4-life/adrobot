from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.campaigns.drafts import DraftError
from app.tracker.port import TrackerError

STATUS = {"not_found": 404, "conflict": 409, "invalid": 422}
TRACKER_FAILED = 502


async def draft_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, DraftError)
    return JSONResponse(status_code=STATUS[error.kind], content={"detail": error.message})


async def tracker_error(_: Request, error: Exception) -> JSONResponse:
    """The tracker's own message; its status is in the text (never the API key)."""
    assert isinstance(error, TrackerError)
    detail = f"Tracker error ({error.status}): {error.message}"
    return JSONResponse(status_code=TRACKER_FAILED, content={"detail": detail})


def register(app: FastAPI) -> None:
    app.add_exception_handler(DraftError, draft_error)
    app.add_exception_handler(TrackerError, tracker_error)
