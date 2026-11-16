"""Реалізація Actions. Екрани сюди не імпортують: їх підключає main.py.

Кожен метод нижче має зібрати результат із рушія, довідки, погоди і бази.
Порядок для open_zone записаний у docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from datetime import datetime

from app.contracts.models import (
    FarmScore,
    LeaderboardRow,
    Reminder,
    Settings,
    SoilType,
    SpeciesProfile,
    WidgetSnapshot,
    Zone,
    ZoneKind,
    ZoneView,
)
from app.core.care import CarePlanner
from app.core.groups import GroupBuilder
from app.core.growth import GrowthEngine
from app.core.score import Scoreboard
from app.knowledge.catalog import FarmingCatalog
from app.knowledge.weather import WeatherService
from app.storage.reminders import ReminderService
from app.storage.store import GardenStore
from app.storage.widgets import WidgetBoard


class GardenActions:
    def __init__(
        self,
        store: GardenStore,
        catalog: FarmingCatalog,
        weather: WeatherService,
        growth: GrowthEngine,
        care: CarePlanner,
        groups: GroupBuilder,
        scores: Scoreboard,
        reminders: ReminderService,
        widgets: WidgetBoard,
    ) -> None:
        self.store = store
        self.catalog = catalog
        self.weather = weather
        self.growth = growth
        self.care = care
        self.groups = groups
        self.scores = scores
        self.reminders = reminders
        self.widgets = widgets

    def list_zones(self) -> list[Zone]:
        raise NotImplementedError("app/wiring/actions.py list_zones")

    def create_zone(self, name: str, kind: ZoneKind, territory: str) -> Zone:
        raise NotImplementedError("app/wiring/actions.py create_zone")

    def open_zone(self, zone_id: str) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py open_zone")

    def search_species(self, query: str) -> list[SpeciesProfile]:
        raise NotImplementedError("app/wiring/actions.py search_species")

    def describe(self, name: str, variety: str, soil: SoilType, zone_id: str) -> SpeciesProfile:
        raise NotImplementedError("app/wiring/actions.py describe")

    def plant(
        self,
        zone_id: str,
        name: str,
        variety: str,
        soil: SoilType,
        x: float,
        y: float,
        planted_at: datetime | None = None,
    ) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py plant")

    def move_pot(self, zone_id: str, pot_id: str, x: float, y: float) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py move_pot")

    def water(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py water")

    def fertilize(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py fertilize")

    def harvest(self, zone_id: str, pot_id: str) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py harvest")

    def group_crops(self, zone_id: str) -> ZoneView:
        raise NotImplementedError("app/wiring/actions.py group_crops")

    def shift_days(self, delta: int) -> int:
        raise NotImplementedError("app/wiring/actions.py shift_days")

    def get_settings(self) -> Settings:
        raise NotImplementedError("app/wiring/actions.py get_settings")

    def save_settings(self, settings: Settings) -> Settings:
        raise NotImplementedError("app/wiring/actions.py save_settings")

    def your_score(self, zone_id: str) -> FarmScore:
        raise NotImplementedError("app/wiring/actions.py your_score")

    def leaderboard(self, zone_id: str) -> list[LeaderboardRow]:
        raise NotImplementedError("app/wiring/actions.py leaderboard")

    def add_friend(self, nickname: str, points: int) -> list[LeaderboardRow]:
        raise NotImplementedError("app/wiring/actions.py add_friend")

    def widgets(self) -> list[WidgetSnapshot]:
        raise NotImplementedError("app/wiring/actions.py widgets")

    def due_reminders(self) -> list[Reminder]:
        raise NotImplementedError("app/wiring/actions.py due_reminders")
