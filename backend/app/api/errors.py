from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.campaigns.drafts import DraftError

STATUS = {"not_found": 404, "conflict": 409, "invalid": 422}


async def draft_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, DraftError)
    return JSONResponse(status_code=STATUS[error.kind], content={"detail": error.message})


def register(app: FastAPI) -> None:
    app.add_exception_handler(DraftError, draft_error)
