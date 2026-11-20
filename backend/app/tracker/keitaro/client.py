"""Async client for the Keitaro Admin API: only the endpoints AdRobot uses.

Reads are retried on 5xx and network errors. Writes never are: a failed write is resumed by
the next push. The API key is sent as a header and never appears in errors or logs.
"""

import asyncio
from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import BaseModel, TypeAdapter

from app.config import settings
from app.tracker.keitaro.models_overrides import (
    Campaign,
    CampaignRequest,
    Domain,
    Group,
    Offer,
    Source,
    Stream,
    StreamObject,
)

API_PATH = "/admin_api/v1"
NETWORK_ERROR = 0  # KeitaroError.status when no response came back
ERROR_TEXT_LIMIT = 200

_CAMPAIGNS = TypeAdapter(list[Campaign])
_CAMPAIGN = TypeAdapter(Campaign)
_STREAMS = TypeAdapter(list[Stream])
_STREAM = TypeAdapter(Stream)
_OFFERS = TypeAdapter(list[Offer])
_DOMAINS = TypeAdapter(list[Domain])
_GROUPS = TypeAdapter(list[Group])
_SOURCES = TypeAdapter(list[Source])


class KeitaroError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Keitaro {status}: {message}")
        self.status = status
        self.message = message


def _error_message(response: httpx.Response) -> str:
    """Keitaro's `{"error": "..."}` body, else the start of the raw body."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:ERROR_TEXT_LIMIT] or response.reason_phrase
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, str):
        return error
    return str(body)[:ERROR_TEXT_LIMIT]


def _json(response: httpx.Response) -> Any:
    if response.is_error:
        raise KeitaroError(response.status_code, _error_message(response))
    return response.json()


def _payload(model: BaseModel) -> dict[str, Any]:
    """Only the fields that were set: schema defaults are never sent by accident."""
    return model.model_dump(mode="json", by_alias=True, exclude_unset=True)


class KeitaroClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        read_retries: int = 2,
        retry_delay: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + API_PATH,
            headers={"Api-Key": api_key},
            timeout=timeout,
            transport=transport,
        )
        self._read_retries = read_retries
        self._retry_delay = retry_delay

    @classmethod
    def from_settings(cls) -> Self:
        return cls(
            settings.keitaro_url,
            settings.keitaro_api_key,
            timeout=settings.keitaro_timeout_seconds,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- reads ---

    async def list_campaigns(self, page_size: int = 500) -> list[Campaign]:
        campaigns: list[Campaign] = []
        offset = 0
        while True:
            params = {"offset": offset, "limit": page_size}
            page = _CAMPAIGNS.validate_python(await self._read("/campaigns", params))
            campaigns.extend(page)
            if len(page) < page_size:
                return campaigns
            offset += page_size

    async def list_streams(self, campaign_id: int) -> list[Stream]:
        return _STREAMS.validate_python(await self._read(f"/campaigns/{campaign_id}/streams"))

    async def get_stream(self, stream_id: int) -> Stream:
        return _STREAM.validate_python(await self._read(f"/streams/{stream_id}"))

    async def list_offers(self) -> list[Offer]:
        return _OFFERS.validate_python(await self._read("/offers"))

    async def list_domains(self) -> list[Domain]:
        return _DOMAINS.validate_python(await self._read("/domains"))

    async def list_groups(self) -> list[Group]:
        return _GROUPS.validate_python(await self._read("/groups", {"type": "campaigns"}))

    async def list_sources(self) -> list[Source]:
        return _SOURCES.validate_python(await self._read("/traffic_sources"))

    # --- writes ---

    async def create_campaign(self, payload: CampaignRequest) -> Campaign:
        return _CAMPAIGN.validate_python(await self._write("POST", "/campaigns", payload))

    async def create_stream(self, payload: StreamObject) -> Stream:
        return _STREAM.validate_python(await self._write("POST", "/streams", payload))

    async def update_stream(self, stream_id: int, payload: StreamObject) -> Stream:
        response = await self._write("PUT", f"/streams/{stream_id}", payload)
        return _STREAM.validate_python(response)

    # --- transport ---

    async def _read(self, path: str, params: Mapping[str, str | int] | None = None) -> Any:
        for attempt in range(self._read_retries + 1):
            last = attempt == self._read_retries
            try:
                response = await self._http.get(path, params=params)
            except httpx.TransportError as error:
                if last:
                    raise _network_error(error) from error
            else:
                if response.status_code < 500 or last:
                    return _json(response)
            await asyncio.sleep(self._retry_delay * 2**attempt)
        raise AssertionError("unreachable")

    async def _write(self, method: str, path: str, payload: BaseModel) -> Any:
        try:
            response = await self._http.request(method, path, json=_payload(payload))
        except httpx.TransportError as error:
            raise _network_error(error) from error
        return _json(response)


def _network_error(error: httpx.TransportError) -> KeitaroError:
    return KeitaroError(NETWORK_ERROR, f"network error ({type(error).__name__})")
