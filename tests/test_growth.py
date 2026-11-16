"""Рушій app/core проти docs/RULES.md. Час фіксований, UTC."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.contracts.constants import MAX_SIM_DAYS
from app.contracts.models import (
    CareAction,
    CareEvent,
    CropGroup,
    FarmScore,
    Friend,
    GrowthForecast,
    GrowthStage,
    Mood,
    PlantingProfile,
    Pot,
    SoilType,
    SpeciesProfile,
    Zone,
    ZoneKind,
)
from app.contracts.samples import sample_species
from app.core.care import TIP_FERTILIZE, TIP_HARVEST, TIP_WATER_NOW, CarePlanner, water_interval_days
from app.core.forecast import forecast
from app.core.groups import GroupBuilder
from app.core.growth import GrowthEngine, _apply_event, _State
from app.core.score import Scoreboard

T0 = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
ZONE_ID = "zone-test"


def cucumber() -> SpeciesProfile:
    return sample_species()[0]


def tomato() -> SpeciesProfile:
    return sample_species()[1]


def profile(
    species: SpeciesProfile,
    soil: SoilType = SoilType.LOAM,
    kind: ZoneKind = ZoneKind.GREENHOUSE,
) -> PlantingProfile:
    return PlantingProfile(
        species_id=species.species_id,
        variety=species.variety,
        soil_type=soil,
        territory="Київ",
        zone_kind=kind,
        planted_at=T0,
    )


def day(n: float) -> datetime:
    return T0 + timedelta(days=n)


class Garden:
    """Маленький журнал: посадити, додати події, перерахувати."""

    def __init__(self, species: SpeciesProfile, soil: SoilType = SoilType.LOAM, kind: ZoneKind = ZoneKind.GREENHOUSE) -> None:
        self.engine = GrowthEngine()
        self.species = species
        self.pot, first = self.engine.plant(ZONE_ID, profile(species, soil, kind), 100.0, 200.0, species)
        self.events: list[CareEvent] = [first]

    def add(self, action: CareAction, at: datetime) -> None:
        self.events.append(self.engine.make_event(self.pot.id, action, at))

    def water_daily(self, days: int) -> None:
        for n in range(1, days + 1):
            self.add(CareAction.WATER, day(n))

    def at(self, when: datetime) -> Pot:
        return self.engine.advance(self.pot, self.species, list(self.events), when)


class GrowthTests(unittest.TestCase):
    def test_1_planting_moment(self) -> None:
        garden = Garden(cucumber())
        pot = garden.pot
        self.assertEqual(pot.stage, GrowthStage.SPROUT)
        self.assertEqual(pot.stage_progress, 0)
        self.assertEqual(pot.moisture, 0.8)
        self.assertEqual(pot.fertility, 0.6)
        self.assertEqual(pot.health, 0.9)
        self.assertIsNone(pot.group_id)
        self.assertEqual((pot.x, pot.y, pot.zone_id), (100.0, 200.0, ZONE_ID))
        self.assertEqual(garden.events[0].action, CareAction.PLANT)
        self.assertEqual(garden.events[0].pot_id, pot.id)

    def test_1b_non_ideal_soil_starts_weaker(self) -> None:
        pot = Garden(cucumber(), soil=SoilType.SAND).pot
        self.assertEqual(pot.health, 0.7)

    def test_1c_plant_equals_advance_at_planting(self) -> None:
        garden = Garden(cucumber())
        self.assertEqual(garden.at(T0), garden.pot)

    def test_2_intervals(self) -> None:
        species = cucumber()
        sand = water_interval_days(species, profile(species, SoilType.SAND))
        clay = water_interval_days(species, profile(species, SoilType.CLAY))
        self.assertLess(sand, clay)
        greenhouse = water_interval_days(species, profile(species, SoilType.LOAM, ZoneKind.GREENHOUSE))
        garden = water_interval_days(species, profile(species, SoilType.LOAM, ZoneKind.GARDEN))
        self.assertLess(greenhouse, garden)
        self.assertEqual(greenhouse, 1.7)
        self.assertEqual(CarePlanner().interval_days(species, profile(species, SoilType.SAND)), sand)

    def test_2b_interval_floor(self) -> None:
        species = replace(cucumber(), water_every_days=0.1)
        self.assertEqual(water_interval_days(species, profile(species, SoilType.SAND)), 0.5)

    def test_3_late_watering_keeps_moisture_high(self) -> None:
        garden = Garden(cucumber())
        garden.add(CareAction.WATER, day(10) - timedelta(hours=1))
        pot = garden.at(day(10))
        self.assertGreater(pot.moisture, 0.9)
        self.assertNotIn(pot.mood, (Mood.THIRSTY, Mood.SAD))

    def test_4_no_water_is_sad(self) -> None:
        garden = Garden(cucumber())
        pot = garden.at(day(10))
        self.assertEqual(pot.mood, Mood.SAD)
        self.assertLess(pot.health, garden.pot.health)
        self.assertEqual(pot.moisture, 0.0)

    def test_5_advance_is_pure(self) -> None:
        garden = Garden(cucumber())
        garden.water_daily(12)
        garden.add(CareAction.FERTILIZE, day(5))
        moved = replace(garden.pot, x=999.0, y=1.0, group_id="g1", moisture=0.01, health=0.01)
        first = garden.engine.advance(moved, garden.species, list(garden.events), day(12.5))
        second = garden.engine.advance(moved, garden.species, list(reversed(garden.events)), day(12.5))
        self.assertEqual(first, second)
        self.assertEqual((first.x, first.y, first.group_id), (999.0, 1.0, "g1"))

    def test_6_early_harvest_is_ignored(self) -> None:
        garden = Garden(cucumber())
        garden.water_daily(10)
        before = garden.at(day(10))
        garden.add(CareAction.HARVEST, day(9))
        after = garden.at(day(10))
        self.assertNotEqual(before.stage, GrowthStage.RIPE)
        self.assertEqual(after, before)

    def test_7_regrowing_harvest_returns_to_flowering(self) -> None:
        garden = Garden(cucumber())
        garden.water_daily(60)
        ripe = garden.at(day(55))
        self.assertEqual(ripe.stage, GrowthStage.RIPE)
        garden.add(CareAction.HARVEST, day(55))
        after = garden.at(day(55))
        self.assertEqual(after.stage, GrowthStage.FLOWERING)
        self.assertEqual(after.stage_progress, 0)

    def test_7b_single_harvest_stops_growth(self) -> None:
        species = replace(tomato(), regrows=False)
        garden = Garden(species)
        garden.water_daily(90)
        self.assertEqual(garden.at(day(80)).stage, GrowthStage.RIPE)
        garden.add(CareAction.HARVEST, day(80))
        for later in (80, 85, 120, 300):
            self.assertEqual(garden.at(day(later)).stage, GrowthStage.HARVESTED)
        self.assertLess(garden.at(day(120)).moisture, garden.at(day(81)).moisture + 1e-9)

    def test_8_fertilizer_when_rich_hurts(self) -> None:
        state = _State(moisture=0.6, fertility=0.95, health=0.8)
        _apply_event(state, CareAction.FERTILIZE, cucumber())
        self.assertAlmostEqual(state.health, 0.75)
        self.assertEqual(state.fertility, 0.95)

        garden = Garden(cucumber())
        garden.add(CareAction.FERTILIZE, day(0.5))
        garden.add(CareAction.FERTILIZE, day(0.5))
        two = garden.at(day(0.6))
        self.assertEqual(two.fertility, 1.0)
        garden.add(CareAction.FERTILIZE, day(0.5))
        three = garden.at(day(0.6))
        self.assertEqual(three.fertility, 1.0)
        self.assertAlmostEqual(three.health, two.health - 0.05)

    def test_watering_wet_soil_hurts(self) -> None:
        garden = Garden(cucumber())
        garden.add(CareAction.WATER, T0)
        once = garden.at(T0)
        garden.add(CareAction.WATER, T0)
        twice = garden.at(T0)
        self.assertEqual(once.moisture, 0.95)
        self.assertEqual(once.health, 0.9)
        self.assertAlmostEqual(twice.health, 0.87)

    def test_time_before_planting_and_cap(self) -> None:
        garden = Garden(cucumber())
        self.assertEqual(garden.at(T0 - timedelta(days=5)), garden.pot)
        capped = garden.at(day(MAX_SIM_DAYS))
        self.assertEqual(garden.at(day(MAX_SIM_DAYS + 50)), capped)

    def test_naive_time_is_utc(self) -> None:
        garden = Garden(cucumber())
        self.assertEqual(garden.at(day(3).replace(tzinfo=None)), garden.at(day(3)))

    def test_other_pot_events_ignored(self) -> None:
        garden = Garden(cucumber())
        foreign = CareEvent(id="x", pot_id="someone-else", action=CareAction.WATER, at=day(2))
        self.assertEqual(
            garden.engine.advance(garden.pot, garden.species, garden.events + [foreign], day(3)),
            garden.at(day(3)),
        )


class CareTests(unittest.TestCase):
    def test_next_water_from_last_watering(self) -> None:
        garden = Garden(cucumber())
        garden.add(CareAction.WATER, day(2))
        garden.add(CareAction.WATER, day(4))
        garden.add(CareAction.WATER, day(9))  # ще не настав
        pot = garden.at(day(5))
        plan = CarePlanner().plan(pot, garden.species, garden.events, day(5))
        self.assertEqual(plan.water_every_days, 1.7)
        self.assertEqual(plan.next_water_at, day(4) + timedelta(days=1.7))
        self.assertEqual(plan.next_fertilize_at, day(14))
        self.assertEqual(plan.pot_id, pot.id)

    def test_tips_order_and_limit(self) -> None:
        species = replace(cucumber(), tips=("a", "b", "c"))
        pot = replace(Garden(species).pot, mood=Mood.SAD, fertility=0.2, stage=GrowthStage.RIPE)
        tips = CarePlanner().plan(pot, species, [], T0).tips
        self.assertEqual(tips, (TIP_WATER_NOW, TIP_FERTILIZE, TIP_HARVEST, "a"))

    def test_healthy_pot_gets_species_tips(self) -> None:
        garden = Garden(cucumber())
        tips = CarePlanner().plan(garden.pot, garden.species, garden.events, T0).tips
        self.assertEqual(tips, cucumber().tips)


def _pot(pot_id: str, species: SpeciesProfile, x: float, y: float, group_id: str | None = None) -> Pot:
    base, _ = GrowthEngine().plant(ZONE_ID, profile(species), x, y, species)
    return replace(base, id=pot_id, group_id=group_id)


class GroupTests(unittest.TestCase):
    titles = {"cucumber": "Огірок", "tomato": "Помідор"}

    def test_10_two_pots_no_group(self) -> None:
        groups, pots = GroupBuilder().suggest([_pot("a", cucumber(), 0, 0), _pot("b", cucumber(), 10, 0)], [], self.titles)
        self.assertEqual(groups, [])
        self.assertTrue(all(pot.group_id is None for pot in pots))

    def test_10_three_make_group_fourth_joins(self) -> None:
        builder = GroupBuilder()
        three = [_pot("a", cucumber(), 0, 0), _pot("b", cucumber(), 30, 0), _pot("c", cucumber(), 0, 30), _pot("t", tomato(), 500, 500)]
        groups, pots = builder.suggest(three, [], self.titles)
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.title, "Група: Огірок")
        self.assertEqual(group.species_id, "cucumber")
        self.assertEqual(group.zone_id, ZONE_ID)
        self.assertEqual(group.pot_ids, ("a", "b", "c"))
        self.assertEqual((group.x, group.y), (10.0, 10.0))
        self.assertIsNone(next(p for p in pots if p.id == "t").group_id)

        groups2, pots2 = builder.suggest(pots + [_pot("d", cucumber(), 40, 40)], groups, self.titles)
        self.assertEqual(len(groups2), 1)
        self.assertEqual(groups2[0].id, group.id)
        self.assertEqual(groups2[0].pot_ids, ("a", "b", "c", "d"))
        self.assertEqual((groups2[0].x, groups2[0].y), (17.5, 17.5))

    def test_missing_group_is_removed_and_title_fallback(self) -> None:
        pots = [_pot(i, tomato(), 0, 0, group_id="ghost") for i in "xyz"]
        groups, out = GroupBuilder().suggest(pots, [], {})
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].title, "Група: tomato")
        self.assertTrue(all(p.group_id == groups[0].id for p in out))

    def test_foreign_species_not_added_and_no_moving(self) -> None:
        existing = [
            CropGroup(id="g-cu", zone_id=ZONE_ID, species_id="cucumber", title="Група: Огірок", pot_ids=("a",), x=0, y=0),
            CropGroup(id="g-cu2", zone_id=ZONE_ID, species_id="cucumber", title="Група: Огірок", pot_ids=("b",), x=0, y=0),
        ]
        pots = [_pot("a", cucumber(), 0, 0, "g-cu"), _pot("b", cucumber(), 10, 10, "g-cu2"), _pot("t", tomato(), 5, 5, "g-cu")]
        groups, out = GroupBuilder().suggest(pots, existing, self.titles)
        by_id = {p.id: p for p in out}
        self.assertEqual(by_id["a"].group_id, "g-cu")
        self.assertEqual(by_id["b"].group_id, "g-cu2")
        self.assertIsNone(by_id["t"].group_id)
        self.assertEqual({g.id: g.pot_ids for g in groups}, {"g-cu": ("a",), "g-cu2": ("b",)})


class ScoreTests(unittest.TestCase):
    zone = Zone(id=ZONE_ID, name="Теплиця", kind=ZoneKind.GREENHOUSE, territory="Київ")

    def test_9_empty_zone_scores_zero(self) -> None:
        score = Scoreboard().score_zone(self.zone, [], [], "Я")
        self.assertEqual((score.points, score.health, score.ripe_count), (0, 0.0, 0))

    def test_points_formula(self) -> None:
        a = replace(_pot("a", cucumber(), 0, 0), health=0.8, stage=GrowthStage.RIPE)
        b = replace(_pot("b", cucumber(), 0, 0), health=0.6)
        harvest = CareEvent(id="h", pot_id="a", action=CareAction.HARVEST, at=T0)
        water = CareEvent(id="w", pot_id="a", action=CareAction.WATER, at=T0)
        score = Scoreboard().score_zone(self.zone, [a, b], [harvest, water], "Я")
        self.assertEqual(score.ripe_count, 1)
        self.assertEqual(score.points, round(100 * 0.7 + 25 + 15))
        self.assertEqual(score.nickname, "Я")
        self.assertEqual(score.zone_id, ZONE_ID)

    def test_11_tie_puts_you_first(self) -> None:
        you = FarmScore(zone_id=ZONE_ID, nickname="Я", health=0.5, ripe_count=0, points=50)
        rows = Scoreboard().leaderboard(you, [Friend(id="1", nickname="Аня", points=50), Friend(id="2", nickname="Боб", points=90)])
        self.assertEqual([r.nickname for r in rows], ["Боб", "Я", "Аня"])
        self.assertTrue(rows[1].is_you)
        self.assertEqual(sum(r.is_you for r in rows), 1)


class ForecastTests(unittest.TestCase):
    def test_fresh_pot_full_health_speed(self) -> None:
        pot = replace(Garden(cucumber()).pot, health=1.0)
        result = forecast(pot, cucumber(), T0)
        self.assertEqual(result.next_stage, GrowthStage.GROWING)
        self.assertEqual(result.next_stage_at, day(7))
        self.assertEqual(result.ripe_at, day(47))

    def test_middle_of_stage_and_bad_soil(self) -> None:
        pot = replace(Garden(cucumber(), soil=SoilType.SAND).pot, stage=GrowthStage.GROWING, stage_progress=0.5, health=1.0)
        result = forecast(pot, cucumber(), T0)
        # кредит 7 + 12 = 19; швидкість 0.8; до цвітіння 12 / 0.8 = 15 діб
        self.assertEqual(result.next_stage, GrowthStage.FLOWERING)
        self.assertEqual(result.next_stage_at, day(15))
        self.assertEqual(result.ripe_at, day(28 / 0.8))

    def test_slower_variety_ripens_later(self) -> None:
        slow = replace(cucumber(), variety="повільний", stage_days={"sprout": 10, "growing": 30, "flowering": 10, "fruiting": 10, "ripe": 10})
        fast_pot = replace(Garden(cucumber()).pot, health=1.0)
        self.assertLess(forecast(fast_pot, cucumber(), T0).ripe_at, forecast(fast_pot, slow, T0).ripe_at)

    def test_zero_day_stage_is_skipped(self) -> None:
        carrot_like = replace(cucumber(), stage_days={"sprout": 5, "growing": 10, "flowering": 0, "fruiting": 8, "ripe": 4})
        pot = replace(Garden(carrot_like).pot, stage=GrowthStage.GROWING, stage_progress=0.0, health=1.0)
        self.assertEqual(forecast(pot, carrot_like, T0).next_stage, GrowthStage.FRUITING)

    def test_ripe_has_no_forecast(self) -> None:
        pot = replace(Garden(cucumber()).pot, stage=GrowthStage.RIPE)
        self.assertEqual(forecast(pot, cucumber(), T0), GrowthForecast(None, None, None))


if __name__ == "__main__":
    unittest.main()
