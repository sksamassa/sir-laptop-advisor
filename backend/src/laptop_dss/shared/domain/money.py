"""Money is stored and transported as integer kopecks (Principle IV)."""

from __future__ import annotations

from decimal import Decimal

KOPECKS_PER_RUBLE = 100


def rubles(amount_minor: int) -> Decimal:
    """Render kopecks as rubles for display only."""
    return Decimal(amount_minor) / KOPECKS_PER_RUBLE


def format_rub(amount_minor: int) -> str:
    """Format kopecks as a Russian ruble string, e.g. ``64 990 ₽``."""
    whole, frac = divmod(amount_minor, KOPECKS_PER_RUBLE)
    whole_str = f"{whole:,}".replace(",", " ")
    if frac:
        return f"{whole_str},{frac:02d} ₽"
    return f"{whole_str} ₽"
