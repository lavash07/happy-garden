"""Каркас має імпортуватися і тримати однакові методи між папками."""

from __future__ import annotations

import inspect
import json
import unittest
from dataclasses import replace
from pathlib import Path

from app.contracts.checks import clamp_world, clean_friend, clean_zone_name
from app.contracts.clock import real_now, sim_now
from app.contracts.codec import pot_from_dict, pot_to_dict, settings_from_dict, species_from_dict
from app.contracts.fakes import DEMO_RIPE_POT, FakeActions
from app.contracts.models import GrowthStage, Settings, SoilType, ZoneKind
from app.contracts.ports import (
    Actions,
    CarePort,
    GroupPort,
    GrowthPort,
    KnowledgePort,
    ReminderPort,
    ScorePort,
    StorePort,
    WeatherPort,
    WidgetPort,
)
from app.contracts.samples import SAMPLE_ZONE_ID, sample_zone_view
from app.contracts.timeline import ideal_timeline
from app.core.care import CarePlanner
from app.core.groups import GroupBuilder
from app.core.growth import GrowthEngine
from app.core.score import Scoreboard
from app.knowledge.catalog import FarmingCatalog
from app.knowledge.weather import WeatherService
from app.storage.reminders import ReminderService
from app.storage.store import GardenStore
from app.storage.widgets import WidgetBoard
from app.wiring.actions import GardenActions

ROOT = Path(__file__).resolve().parents[1]


def _methods(obj: object) -> set[str]:
    return {
        name
        for name, value in inspect.getmembers(obj)
        if (inspect.isfunction(value) or inspect.ismethod(value)) and not name.startswith("_")
    }


class SurfaceTests(unittest.TestCase):
    def test_actions_match(self) -> None:
        expected = _methods(Actions)
        self.assertEqual(_methods(GardenActions), expected)
        self.assertEqual(_methods(FakeActions), expected)

    def test_engines_match_ports(self) -> None:
        pairs = (
            (GrowthEngine, GrowthPort),
            (CarePlanner, CarePort),
            (GroupBuilder, GroupPort),
            (Scoreboard, ScorePort),
            (FarmingCatalog, KnowledgePort),
            (WeatherService, WeatherPort),
            (GardenStore, StorePort),
            (ReminderService, ReminderPort),
            (WidgetBoard, WidgetPort),
        )
        for impl, port in pairs:
            self.assertEqual(_methods(impl), _methods(port), impl.__name__)


class ContractTests(unittest.TestCase):
    def test_species_file_parses(self) -> None:
        raw = json.loads((ROOT / "app" / "knowledge" / "data" / "species.json").read_text(encoding="utf-8"))
        species = species_from_dict(raw["species"][0])
        self.assertEqual(species.species_id, "cucumber")
        self.assertFalse(species.verified)

    def test_timeline_is_cumulative(self) -> None:
        species = species_from_dict(json.loads((ROOT / "app" / "knowledge" / "data" / "species.json").read_text(encoding="utf-8"))["species"][0])
        marks = ideal_timeline(species)
        self.assertEqual([mark.starts_on_day for mark in marks], [0, 7, 31, 39, 47])
        self.assertEqual(marks[0].label, "Паростки")

    def test_pot_roundtrip(self) -> None:
        pot = sample_zone_view().cards[0].pot
        self.assertEqual(pot_from_dict(pot_to_dict(pot)), pot)

    def test_empty_settings(self) -> None:
        self.assertEqual(settings_from_dict({}), Settings())

    def test_sim_clock_shifts_days(self) -> None:
        shifted = sim_now(replace(Settings(), debug_day_offset=2)) - real_now()
        self.assertAlmostEqual(shifted.total_seconds(), 2 * 86400, delta=5)

    def test_names_and_map_edges(self) -> None:
        self.assertEqual(clean_zone_name("  Теплиця   на  дачі "), "Теплиця на дачі")
        with self.assertRaises(ValueError):
            clean_friend("   ", 1)
        self.assertEqual(clamp_world(-10, 5000), (0.0, 2000.0))


class FakeTests(unittest.TestCase):
    def test_water_and_harvest_change_the_showcase(self) -> None:
        actions = FakeActions()
        watered = actions.water(SAMPLE_ZONE_ID, "pot-c2")
        pot = next(card.pot for card in watered.cards if card.pot.id == "pot-c2")
        self.assertEqual(pot.moisture, 0.95)
        harvested = actions.harvest(SAMPLE_ZONE_ID, DEMO_RIPE_POT)
        ripe = next(card.pot for card in harvested.cards if card.pot.id == DEMO_RIPE_POT)
        self.assertEqual(ripe.stage, GrowthStage.FLOWERING)

    def test_leaderboard_puts_higher_score_first(self) -> None:
        rows = FakeActions().leaderboard(SAMPLE_ZONE_ID)
        self.assertGreater(rows[0].points, rows[1].points)
        self.assertFalse(rows[0].is_you)

    def test_unknown_species(self) -> None:
        from app.contracts.errors import SpeciesNotFound

        with self.assertRaises(SpeciesNotFound):
            FakeActions().describe("манго", "", SoilType.LOAM, SAMPLE_ZONE_ID)

    def test_create_zone_and_plant(self) -> None:
        actions = FakeActions()
        zone = actions.create_zone("Поле", ZoneKind.FARM, "Львів")
        view = actions.plant(zone.id, "помідор", "Рожевий", SoilType.CHERNOZEM, -5, 10)
        self.assertEqual(len(view.cards), 1)
        self.assertEqual(view.cards[0].pot.x, 0.0)
        self.assertEqual(view.cards[0].species.species_id, "tomato")


if __name__ == "__main__":
    unittest.main()
