"""Domain event port. Contexts publish facts; subscribers react in-process."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


Handler = Callable[[DomainEvent], None]


class Claim(Protocol):
    """Returns True only the first time this (event, handler) pair is seen."""

    def __call__(self, event_id: uuid.UUID, handler: str) -> bool: ...


class EventBus(Protocol):
    def subscribe(self, event_name: str, handler: Handler, *, name: str | None = None) -> None: ...

    def publish(self, event: DomainEvent) -> int: ...
