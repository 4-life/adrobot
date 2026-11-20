"""Composition root for the tracker port: the one place that picks the adapter (`TRACKER`)."""

from app.config import settings
from app.tracker.port import TrackerProvider


def create_tracker() -> TrackerProvider:
    if settings.tracker == "keitaro":
        from app.tracker.keitaro import adapter

        return adapter.create()
    if settings.tracker == "fake":
        from app.tracker.fake import adapter as fake

        return fake.create()
    raise ValueError(f"unknown TRACKER: {settings.tracker!r}")
