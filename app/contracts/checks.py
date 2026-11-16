"""Перевірки полів форм. І фейк, і справжній фасад кличуть саме їх."""

from __future__ import annotations

from app.contracts.constants import DEFAULT_TERRITORY, DEFAULT_VARIETY, WORLD_SIZE


def _clean(value: str, max_len: int, message: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= max_len:
        raise ValueError(message)
    return name


def clean_zone_name(value: str) -> str:
    return _clean(value, 30, "Назва зони від 1 до 30 символів")


def clean_nickname(value: str) -> str:
    return _clean(value, 20, "Нік від 1 до 20 символів")


def clean_friend(nickname: str, points: int) -> tuple[str, int]:
    name = clean_nickname(nickname)
    if isinstance(points, bool) or not isinstance(points, int) or not 0 <= points <= 99_999:
        raise ValueError("Очки — ціле число від 0 до 99999")
    return name, points


def clean_variety(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        return DEFAULT_VARIETY
    if len(name) > 40:
        raise ValueError("Сорт до 40 символів")
    return name


def clean_territory(value: str, fallback: str = DEFAULT_TERRITORY) -> str:
    name = " ".join(value.split())
    if not name:
        name = " ".join(fallback.split()) or DEFAULT_TERRITORY
    if len(name) > 60:
        raise ValueError("Місцевість до 60 символів")
    return name


def clean_species_query(value: str) -> str:
    name = " ".join(value.split())
    if len(name) > 40:
        raise ValueError("Назва культури до 40 символів")
    return name


def clamp_world(x: float, y: float) -> tuple[float, float]:
    limit = WORLD_SIZE

    def one(value: float) -> float:
        number = float(value)
        if number < 0:
            return 0.0
        if number > limit:
            return limit
        return number

    return one(x), one(y)
