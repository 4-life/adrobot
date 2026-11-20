"""Fixes for where Keitaro's schema doesn't match what its API really sends or accepts.

models.py is generated (scripts/gen-keitaro.sh) and never edited; everything else imports
Keitaro models from here.
"""

from typing import Any

from app.tracker.keitaro import models

Domain = models.Domain
Group = models.Group
OfferStream = models.OfferStream
OfferStreamRequest = models.OfferStreamRequest
Source = models.Source


class Campaign(models.Campaign):
    """What GET /campaigns really returns, where the schema's `Campaign` differs."""

    # The schema allows only "s" / "sl" / "slo"; Keitaro sends "" when binding is off.
    bind_visitors: str | None = None  # type: ignore[assignment]
    # Left out of the schema's `Campaign`.
    domain_id: int | None = None
    domain: str | None = None  # the domain's URL, e.g. "https://example.com/"
    group: str | None = None  # the group's name; "" without a group


class Offer(models.Offer):
    """The schema types `values` and `country` as lists; Keitaro sends "" when they're empty.
    AdRobot reads neither, so any shape is accepted."""

    values: Any = None
    country: Any = None


class CampaignRequest(models.CampaignRequest):
    """The schema types `group_id` as a string here; campaigns carry it as an integer."""

    group_id: int | None = None  # type: ignore[assignment]


class Filter(models.Filter):
    """The schema types `payload` as a string; filters like `country` carry a list. It types
    `oid` as a string; Keitaro sends a number."""

    payload: Any = None
    oid: int | str | None = None  # type: ignore[assignment]


class Stream(models.Stream):
    filters: list[Filter] | None = None  # type: ignore[assignment]


class FilterStreamRequest(models.FilterStreamRequest):
    """The schema says a list of strings; a pushed-back filter may carry another shape."""

    payload: Any = None


class StreamObject(models.StreamObject):
    filters: list[FilterStreamRequest] | None = None  # type: ignore[assignment]
