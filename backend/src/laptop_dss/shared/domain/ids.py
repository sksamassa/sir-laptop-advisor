"""Identifier helpers and the clock port."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Deterministic clock for tests."""

    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment
