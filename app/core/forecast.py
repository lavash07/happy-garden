"""Прогноз етапів горщика. Формула — docs/RULES.md, розділ «Прогноз»."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.contracts.models import STAGE_ORDER, GrowthForecast, GrowthStage, Pot, SoilType, SpeciesProfile
from app.core.timeutil import as_utc


def _stage_starts(species: SpeciesProfile) -> dict[GrowthStage, float]:
    """Кредит днів, з якого починається кожен етап (накопичувально, як у stage_from_credit)."""
    starts: dict[GrowthStage, float] = {}
    total = 0.0
    for stage in STAGE_ORDER:
        starts[stage] = total
        total += float(species.stage_days.get(stage.value, 0))
    return starts


def growth_speed(pot: Pot, species: SpeciesProfile) -> float:
    """Та сама швидкість кредиту, що в advance(), але з поточним здоров'ям."""
    speed = 0.55 + 0.45 * pot.health
    if SoilType(pot.profile.soil_type) != SoilType(species.ideal_soil):
        speed *= 0.8
    return speed


def forecast(pot: Pot, species: SpeciesProfile, now: datetime) -> GrowthForecast:
    """Коли настане наступний етап і стиглість, якщо здоров'я лишиться як зараз."""
    if pot.stage in (GrowthStage.RIPE, GrowthStage.HARVESTED):
        return GrowthForecast(next_stage=None, next_stage_at=None, ripe_at=None)
    now = as_utc(now)
    starts = _stage_starts(species)
    days_here = float(species.stage_days.get(pot.stage.value, 0))
    credit = starts[pot.stage] + pot.stage_progress * days_here
    speed = growth_speed(pot, species)

    order = list(STAGE_ORDER)
    later = order[order.index(pot.stage) + 1 :]
    # Етап з нулем днів проскакує, тож наступний — перший з днями, або стиглість.
    next_stage = next(
        (stage for stage in later if stage == GrowthStage.RIPE or species.stage_days.get(stage.value, 0) > 0),
        GrowthStage.RIPE,
    )

    def at(target: float) -> datetime:
        return now + timedelta(days=max(0.0, target - credit) / speed)

    return GrowthForecast(
        next_stage=next_stage,
        next_stage_at=at(starts[next_stage]),
        ripe_at=at(starts[GrowthStage.RIPE]),
    )
