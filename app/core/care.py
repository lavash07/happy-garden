"""Інтервал поливу і найближчі нагадування. Формули — docs/RULES.md, розділи «Полив: інтервал» і «План догляду»."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.contracts.constants import MIN_WATER_INTERVAL_DAYS
from app.contracts.models import (
    CareAction,
    CareEvent,
    CarePlan,
    GrowthStage,
    Mood,
    PlantingProfile,
    Pot,
    SoilType,
    SpeciesProfile,
    ZoneKind,
)
from app.core.timeutil import as_utc

TIP_WATER_NOW = "Полий сьогодні"
TIP_FERTILIZE = "Час удобрити"
TIP_HARVEST = "Можна збирати"
MAX_TIPS = 4
LOW_FERTILITY = 0.35

_SOIL_FACTOR: dict[SoilType, float] = {
    SoilType.SAND: 0.7,
    SoilType.CLAY: 1.25,
    SoilType.PEAT: 1.05,
    SoilType.CHERNOZEM: 1.0,
    SoilType.LOAM: 1.0,
}

_ZONE_FACTOR: dict[ZoneKind, float] = {
    ZoneKind.GREENHOUSE: 0.85,
    ZoneKind.FARM: 1.1,
    ZoneKind.GARDEN: 1.0,
}


def water_interval_days(species: SpeciesProfile, profile: PlantingProfile) -> float:
    """Єдина функція інтервалу поливу. Її ж імпортує GrowthEngine.advance."""
    days = float(species.water_every_days)
    days *= _SOIL_FACTOR[SoilType(profile.soil_type)]
    days *= _ZONE_FACTOR[ZoneKind(profile.zone_kind)]
    return max(MIN_WATER_INTERVAL_DAYS, round(days, 2))


def _last_event_at(
    events: list[CareEvent],
    pot_id: str,
    action: CareAction,
    planted_at: datetime,
    now: datetime,
) -> datetime:
    """Остання подія дії між посадкою і now. Без такої події — дата посадки."""
    last = planted_at
    for event in events:
        if event.pot_id != pot_id or event.action != action:
            continue
        at = as_utc(event.at)
        if planted_at <= at <= now and at > last:
            last = at
    return last


def _tips(pot: Pot, species: SpeciesProfile) -> tuple[str, ...]:
    tips: list[str] = []
    if pot.mood in (Mood.THIRSTY, Mood.SAD):
        tips.append(TIP_WATER_NOW)
    if pot.fertility < LOW_FERTILITY:
        tips.append(TIP_FERTILIZE)
    if pot.stage == GrowthStage.RIPE:
        tips.append(TIP_HARVEST)
    for tip in species.tips:
        if len(tips) >= MAX_TIPS:
            break
        if tip not in tips:
            tips.append(tip)
    return tuple(tips[:MAX_TIPS])


class CarePlanner:
    def interval_days(self, species: SpeciesProfile, profile: PlantingProfile) -> float:
        return water_interval_days(species, profile)

    def plan(
        self,
        pot: Pot,
        species: SpeciesProfile,
        events: list[CareEvent],
        now: datetime,
    ) -> CarePlan:
        """Рахується на вже перерахований advance() горщик. Погода сюди не входить."""
        planted_at = as_utc(pot.profile.planted_at)
        now = max(as_utc(now), planted_at)
        water_every = water_interval_days(species, pot.profile)
        fertilize_every = float(species.fertilize_every_days)
        last_water = _last_event_at(events, pot.id, CareAction.WATER, planted_at, now)
        last_fertilize = _last_event_at(events, pot.id, CareAction.FERTILIZE, planted_at, now)
        return CarePlan(
            pot_id=pot.id,
            water_every_days=water_every,
            fertilize_every_days=fertilize_every,
            next_water_at=last_water + timedelta(days=water_every),
            next_fertilize_at=last_fertilize + timedelta(days=fertilize_every),
            tips=_tips(pot, species),
        )
