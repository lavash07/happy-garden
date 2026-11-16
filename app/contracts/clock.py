"""Два годинники. Симуляція грядки і справжня погода не змішуються."""

from datetime import datetime, timedelta, timezone

from app.contracts.models import Settings


def real_now() -> datetime:
    return datetime.now(timezone.utc)


def sim_now(settings: Settings) -> datetime:
    return real_now() + timedelta(days=settings.debug_day_offset)
