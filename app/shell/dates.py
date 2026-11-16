"""Дати українською для карток: «17 лист», «через 3 дні», «2 дні тому». Без агрономії."""

from __future__ import annotations

from datetime import datetime, timezone

MONTHS = ("січ", "лют", "бер", "квіт", "трав", "черв", "лип", "серп", "вер", "жовт", "лист", "груд")


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def day_month(value: datetime) -> str:
    local = _utc(value).astimezone()
    return f"{local.day} {MONTHS[local.month - 1]}"


def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def span(hours: float) -> str:
    """«5 год», «1 день», «12 днів» — без знака."""
    hours = abs(hours)
    if hours < 1:
        return "менше години"
    if hours < 24:
        n = int(round(hours))
        return f"{n} год"
    n = int(round(hours / 24))
    return f"{n} {_plural(n, 'день', 'дні', 'днів')}"


def relative(value: datetime, now: datetime) -> str:
    """«через 2 дні» або «2 дні тому», «зараз» для меншого за годину."""
    hours = (_utc(value) - _utc(now)).total_seconds() / 3600
    if abs(hours) < 1:
        return "зараз"
    return f"через {span(hours)}" if hours > 0 else f"{span(hours)} тому"


def when(value: datetime, now: datetime) -> str:
    """«17 лист · через 2 дні»."""
    return f"{day_month(value)} · {relative(value, now)}"
