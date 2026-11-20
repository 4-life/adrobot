from typing import Protocol


class Store(Protocol):
    """What the core services need from the database session (an AsyncSession in the app,
    an in-memory fake in tests)."""

    def add(self, instance: object) -> None: ...

    async def commit(self) -> None: ...
