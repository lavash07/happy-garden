"""Дрібні помічники часу і меж для рушія. Усі datetime в ядрі — UTC."""

from __future__ import annotations

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """Наївний час вважаємо UTC, aware переводимо в UTC. Так віднімання не падає."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def clamp(value: float) -> float:
    """Межі від 0 до 1 включно."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
