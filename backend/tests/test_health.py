from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app


class FakeSession:
    async def execute(self, *_: Any) -> None:
        return None


async def fake_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


def test_health() -> None:
    app.dependency_overrides[get_session] = fake_session
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_no_openapi_over_http() -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert TestClient(app).get(path).status_code == 404
