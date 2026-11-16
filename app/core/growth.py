"""Ріст горщика. Формули — docs/RULES.md, розділи «Старт посадки», «Прохід часу», «Стадія з кредиту»."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.contracts.constants import MAX_SIM_DAYS
from app.contracts.ids import new_id
from app.contracts.models import (
    STAGE_ORDER,
    CareAction,
    CareEvent,
    GrowthStage,
    Mood,
    PlantingProfile,
    Pot,
    SoilType,
    SpeciesProfile,
    StageMark,
)
from app.contracts.timeline import ideal_timeline
from app.core.care import water_interval_days
from app.core.timeutil import as_utc, clamp

START_MOISTURE = 0.8
START_FERTILITY = 0.6
START_HEALTH_IDEAL = 0.9
START_HEALTH_OTHER = 0.7

# Події в одну мить: посадка (без ефекту), полив, добриво, збір.
_EVENT_ORDER: dict[CareAction, int] = {
    CareAction.PLANT: 0,
    CareAction.WATER: 1,
    CareAction.FERTILIZE: 2,
    CareAction.HARVEST: 3,
}

_DAY = timedelta(days=1)


@dataclass
class _State:
    moisture: float
    fertility: float
    health: float
    credit: float = 0.0
    harvested: bool = False


def stage_from_credit(credit: float, species: SpeciesProfile) -> tuple[GrowthStage, float]:
    """Етап і частка етапу з накопиченого кредиту днів. Нуль днів — етап проскакує."""
    remaining = credit
    for stage in STAGE_ORDER:
        days = float(species.stage_days.get(stage.value, 0))
        if days <= 0:
            continue
        if remaining < days:
            return stage, clamp(remaining / days)
        remaining -= days
    return GrowthStage.RIPE, 1.0


def _is_ideal_soil(profile: PlantingProfile, species: SpeciesProfile) -> bool:
    return SoilType(profile.soil_type) == SoilType(species.ideal_soil)


def _pass_time(state: _State, hours: float, interval: float, ideal: bool) -> None:
    """Безперервний відрізок без подій: волога падає, кредит росте від здоров'я на початку."""
    if hours <= 0:
        return
    days = hours / 24.0
    speed = 0.55 + 0.45 * state.health
    if not ideal:
        speed *= 0.8
    state.moisture = clamp(state.moisture - days / interval)
    if not state.harvested:
        state.credit += speed * days


def _apply_event(state: _State, action: CareAction, species: SpeciesProfile) -> None:
    if action == CareAction.WATER:
        if state.moisture > 0.85:
            state.health = clamp(state.health - 0.03)
        state.moisture = 0.95
    elif action == CareAction.FERTILIZE:
        if state.fertility >= 0.9:
            state.health = clamp(state.health - 0.05)
        else:
            state.fertility = clamp(state.fertility + 0.25)
    elif action == CareAction.HARVEST:
        if state.harvested:
            return
        stage, _ = stage_from_credit(state.credit, species)
        if stage != GrowthStage.RIPE:
            return
        if species.regrows:
            state.credit = float(
                species.stage_days.get(GrowthStage.SPROUT.value, 0)
                + species.stage_days.get(GrowthStage.GROWING.value, 0)
            )
        else:
            state.harvested = True
    # CareAction.PLANT на показники не впливає.


def _daily_health(state: _State) -> None:
    if state.moisture < 0.2:
        state.health = clamp(state.health - 0.06)
    elif state.moisture < 0.4:
        state.health = clamp(state.health - 0.02)
    elif state.moisture >= 0.5:
        state.health = clamp(state.health + 0.01)


def _mood(moisture: float, health: float) -> Mood:
    if moisture < 0.25 or health < 0.35:
        return Mood.SAD
    if moisture < 0.45:
        return Mood.THIRSTY
    if health > 0.6 and moisture > 0.5:
        return Mood.HAPPY
    return Mood.OK


def _soil_quality(fertility: float, ideal: bool) -> float:
    base = 0.9 if ideal else 0.55
    return clamp(base * (0.75 + 0.25 * fertility))


class GrowthEngine:
    def plant(
        self,
        zone_id: str,
        profile: PlantingProfile,
        x: float,
        y: float,
        species: SpeciesProfile,
    ) -> tuple[Pot, CareEvent]:
        """Горщик і подія PLANT. Стан на мить посадки рахує той самий advance()."""
        blank = Pot(
            id=new_id(),
            zone_id=zone_id,
            profile=profile,
            x=x,
            y=y,
            stage=GrowthStage.SPROUT,
            stage_progress=0.0,
            moisture=0.0,
            soil_quality=0.0,
            fertility=0.0,
            health=0.0,
            mood=Mood.OK,
            group_id=None,
        )
        event = self.make_event(blank.id, CareAction.PLANT, as_utc(profile.planted_at))
        pot = self.advance(blank, species, [event], profile.planted_at)
        return pot, event

    def advance(
        self,
        pot: Pot,
        species: SpeciesProfile,
        events: list[CareEvent],
        now: datetime,
    ) -> Pot:
        """Чиста функція: стан горщика з дати посадки і журналу на мить now.

        З переданого горщика беремо лише id, zone_id, x, y, group_id, profile.
        """
        profile = pot.profile
        start = as_utc(profile.planted_at)
        end = min(max(as_utc(now), start), start + timedelta(days=MAX_SIM_DAYS))
        interval = water_interval_days(species, profile)
        ideal = _is_ideal_soil(profile, species)

        state = _State(
            moisture=START_MOISTURE,
            fertility=START_FERTILITY,
            health=START_HEALTH_IDEAL if ideal else START_HEALTH_OTHER,
        )

        timeline = sorted(
            (
                (as_utc(event.at), _EVENT_ORDER.get(CareAction(event.action), 99), CareAction(event.action))
                for event in events
                if event.pot_id == pot.id and start <= as_utc(event.at) <= end
            ),
            key=lambda item: (item[0], item[1]),
        )

        cursor = start
        index = 0
        tick = start + _DAY
        while True:
            next_event = timeline[index][0] if index < len(timeline) else None
            moment = tick if next_event is None or tick < next_event else next_event
            if moment > end:
                break
            _pass_time(state, (moment - cursor).total_seconds() / 3600.0, interval, ideal)
            cursor = moment
            # Спочатку всі події цієї миті, потім добовий крок здоров'я.
            while index < len(timeline) and timeline[index][0] == moment:
                _apply_event(state, timeline[index][2], species)
                index += 1
            if moment == tick:
                _daily_health(state)
                tick += _DAY
        _pass_time(state, (end - cursor).total_seconds() / 3600.0, interval, ideal)

        if state.harvested:
            stage, progress = GrowthStage.HARVESTED, 1.0
        else:
            stage, progress = stage_from_credit(state.credit, species)

        return Pot(
            id=pot.id,
            zone_id=pot.zone_id,
            profile=profile,
            x=pot.x,
            y=pot.y,
            stage=stage,
            stage_progress=progress,
            moisture=state.moisture,
            soil_quality=_soil_quality(state.fertility, ideal),
            fertility=state.fertility,
            health=state.health,
            mood=_mood(state.moisture, state.health),
            group_id=pot.group_id,
        )

    def timeline(self, profile: PlantingProfile, species: SpeciesProfile) -> list[StageMark]:
        """Нормативний календар. Ґрунт сюди не входить: він впливає лише в advance()."""
        del profile
        return list(ideal_timeline(species))

    def make_event(self, pot_id: str, action: CareAction, now: datetime, note: str = "") -> CareEvent:
        return CareEvent(id=new_id(), pot_id=pot_id, action=action, at=now, note=note)
