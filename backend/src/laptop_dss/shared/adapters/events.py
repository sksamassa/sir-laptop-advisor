"""In-process event bus with durable idempotency.

Each subscription is keyed by (event_id, handler name) in ``processed_events``,
so a replayed event never applies an effect twice (constitution, Principle II).
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from laptop_dss.shared.adapters import db
from laptop_dss.shared.application.events import DomainEvent, Handler

logger = logging.getLogger("laptop_dss.events")


def claim_processed(event_id: uuid.UUID, handler: str) -> bool:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO processed_events (event_id, handler) VALUES (%s, %s) "
            "ON CONFLICT (event_id, handler) DO NOTHING",
            (event_id, handler),
        )
        return cur.rowcount == 1


class InProcessEventBus:
    def __init__(self, claim: Callable[[uuid.UUID, str], bool] | None = claim_processed) -> None:
        self._claim = claim
        self._handlers: dict[str, list[tuple[str, Handler]]] = {}

    def subscribe(self, event_name: str, handler: Handler, *, name: str | None = None) -> None:
        handler_name = name or getattr(handler, "__name__", "handler")
        self._handlers.setdefault(event_name, []).append((handler_name, handler))

    def publish(self, event: DomainEvent) -> int:
        applied = 0
        for handler_name, handler in self._handlers.get(event.name, []):
            if self._claim is not None and not self._claim(event.event_id, handler_name):
                logger.debug(
                    "skip duplicate event=%s handler=%s", event.event_id, handler_name
                )
                continue
            handler(event)
            applied += 1
        return applied


def log_event(event: DomainEvent) -> None:
    logger.info("event=%s id=%s", event.name, event.event_id)


bus = InProcessEventBus()
bus.subscribe("RankingComputed", log_event, name="audit_log")
bus.subscribe("ProfileSaved", log_event, name="audit_log")
bus.subscribe("ModelPublished", log_event, name="audit_log")


def publish(event: DomainEvent) -> int:
    return bus.publish(event)
