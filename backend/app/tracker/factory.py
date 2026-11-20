"""Composition root for the tracker port: the one place that picks the adapter."""

from app.config import settings
from app.tracker.port import TrackerProvider


def create_tracker() -> TrackerProvider:
    if settings.tracker == "keitaro":
        from app.tracker.keitaro import adapter

        return adapter.create()
    raise ValueError(f"unknown TRACKER: {settings.tracker!r}")
