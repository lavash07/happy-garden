"""Вітрина для екранів. Стадії горщиків виставлені руками, це не результат симуляції."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.contracts.codec import species_from_dict
from app.contracts.models import (
    AlertSeverity,
    CarePlan,
    CropGroup,
    GrowthStage,
    Mood,
    PlantingProfile,
    Pot,
    PotCard,
    Reminder,
    SoilType,
    SpeciesProfile,
    WeatherAlert,
    Zone,
    ZoneKind,
    ZoneView,
)
from app.contracts.timeline import ideal_timeline

PLANTED = datetime(2026, 5, 1, tzinfo=timezone.utc)
SAMPLE_ZONE_ID = "zone-demo"
POT_C1 = "pot-c1"
POT_C2 = "pot-c2"
POT_C3 = "pot-c3"
POT_TOMATO = "pot-t1"
GROUP_CUCUMBERS = "group-cucumbers"

_DRAFT = "Чернетка для каркаса. Заміни на перевірену довідку в app/knowledge/data/species.json."


def _species(**overrides: object) -> dict:
    base: dict = {
        "species_id": "cucumber",
        "name": "Огірок",
        "variety": "загальний",
        "category": "vegetable",
        "glyph": "🥒",
        "color_hex": "#2E7D32",
        "regrows": True,
        "verified": False,
        "stage_days": {
            "sprout": 7,
            "growing": 24,
            "flowering": 8,
            "fruiting": 8,
            "ripe": 12,
        },
        "ideal_soil": "loam",
        "soil_ph": [6.0, 7.0],
        "temp_c": [20, 28],
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "summary": _DRAFT,
        "tips": ["Тримай землю вологою, без болота", "Тепло без різких холодних ночей"],
        "sources": [],
    }
    base.update(overrides)
    return base


CUCUMBER_DATA = _species()
TOMATO_DATA = _species(
    species_id="tomato",
    name="Помідор",
    glyph="🍅",
    color_hex="#E53935",
    stage_days={"sprout": 8, "growing": 30, "flowering": 10, "fruiting": 15, "ripe": 20},
    temp_c=[18, 27],
    soil_ph=[6.0, 6.8],
    water_every_days=3,
)
STRAWBERRY_DATA = _species(
    species_id="strawberry",
    name="Полуниця",
    category="fruit",
    glyph="🍓",
    color_hex="#C62828",
    stage_days={"sprout": 14, "growing": 30, "flowering": 15, "fruiting": 10, "ripe": 20},
    temp_c=[15, 25],
    soil_ph=[5.5, 6.5],
    fertilize_every_days=21,
)


def sample_species() -> list[SpeciesProfile]:
    return [
        species_from_dict(CUCUMBER_DATA),
        species_from_dict(TOMATO_DATA),
        species_from_dict(STRAWBERRY_DATA),
    ]


def _profile(species: SpeciesProfile, soil: SoilType = SoilType.LOAM) -> PlantingProfile:
    return PlantingProfile(
        species_id=species.species_id,
        variety=species.variety,
        soil_type=soil,
        territory="Київ",
        zone_kind=ZoneKind.GREENHOUSE,
        planted_at=PLANTED,
    )


def _pot(
    pot_id: str,
    species: SpeciesProfile,
    x: float,
    y: float,
    stage: GrowthStage,
    progress: float,
    moisture: float,
    mood: Mood,
    *,
    health: float,
    fertility: float,
    soil_quality: float,
    group_id: str | None,
    soil: SoilType = SoilType.LOAM,
) -> Pot:
    return Pot(
        id=pot_id,
        zone_id=SAMPLE_ZONE_ID,
        profile=_profile(species, soil),
        x=x,
        y=y,
        stage=stage,
        stage_progress=progress,
        moisture=moisture,
        soil_quality=soil_quality,
        fertility=fertility,
        health=health,
        mood=mood,
        group_id=group_id,
    )


def _plan(pot: Pot, species: SpeciesProfile) -> CarePlan:
    return CarePlan(
        pot_id=pot.id,
        water_every_days=species.water_every_days,
        fertilize_every_days=species.fertilize_every_days,
        next_water_at=PLANTED + timedelta(days=species.water_every_days),
        next_fertilize_at=PLANTED + timedelta(days=species.fertilize_every_days),
        tips=species.tips[:2],
    )


def sample_zone() -> Zone:
    return Zone(id=SAMPLE_ZONE_ID, name="Моя теплиця", kind=ZoneKind.GREENHOUSE, territory="Київ")


def sample_zone_view() -> ZoneView:
    cucumber, tomato, _strawberry = sample_species()
    pots = [
        _pot(POT_C1, cucumber, 400, 500, GrowthStage.SPROUT, 0.2, 0.8, Mood.HAPPY, health=0.9, fertility=0.6, soil_quality=0.9, group_id=GROUP_CUCUMBERS),
        _pot(POT_C2, cucumber, 480, 520, GrowthStage.FRUITING, 0.5, 0.3, Mood.THIRSTY, health=0.6, fertility=0.5, soil_quality=0.7, group_id=GROUP_CUCUMBERS),
        _pot(POT_C3, cucumber, 430, 580, GrowthStage.RIPE, 1.0, 0.72, Mood.HAPPY, health=0.95, fertility=0.8, soil_quality=0.9, group_id=GROUP_CUCUMBERS),
        _pot(POT_TOMATO, tomato, 760, 500, GrowthStage.GROWING, 0.45, 0.18, Mood.SAD, health=0.3, fertility=0.4, soil_quality=0.55, group_id=None, soil=SoilType.SAND),
    ]
    by_id = {cucumber.species_id: cucumber, tomato.species_id: tomato}
    cards = tuple(
        PotCard(pot=pot, species=by_id[pot.profile.species_id], plan=_plan(pot, by_id[pot.profile.species_id]), timeline=ideal_timeline(by_id[pot.profile.species_id]))
        for pot in pots
    )
    group = CropGroup(
        id=GROUP_CUCUMBERS,
        zone_id=SAMPLE_ZONE_ID,
        species_id="cucumber",
        title="Група: Огірок",
        pot_ids=(POT_C1, POT_C2, POT_C3),
        x=440,
        y=530,
    )
    alert = WeatherAlert(
        severity=AlertSeverity.INFO,
        title="Чернетка погоди",
        advice="Справжнє попередження прийде з Open-Meteo.",
        starts_at=PLANTED,
    )
    reminder = Reminder(
        id="rem-demo",
        zone_id=SAMPLE_ZONE_ID,
        pot_id=POT_C2,
        kind="water",
        fire_at=PLANTED,
        title="Полити огірок",
        body="Середній горщик хоче води.",
    )
    return ZoneView(zone=sample_zone(), cards=cards, groups=(group,), alerts=(alert,), reminders=(reminder,))
