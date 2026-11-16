"""Межі між папками. Реалізації живуть у своїх папках і повторюють ці методи."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol

from app.contracts.models import (
    CareAction,
    CareEvent,
    CarePlan,
    CropGroup,
    FarmScore,
    Friend,
    LeaderboardRow,
    PlantingProfile,
    Pot,
    Reminder,
    Settings,
    SoilType,
    SpeciesProfile,
    StageMark,
    WeatherAlert,
    WidgetSnapshot,
    Zone,
    ZoneKind,
    ZoneView,
)


class KnowledgePort(Protocol):
    def search(self, query: str) -> list[SpeciesProfile]: ...

    def find(self, name_or_id: str, variety: str | None = None) -> SpeciesProfile: ...


class WeatherPort(Protocol):
    def alerts(self, territory: str, species: SpeciesProfile, now: datetime) -> list[WeatherAlert]: ...


class GrowthPort(Protocol):
    def plant(
        self,
        zone_id: str,
        profile: PlantingProfile,
        x: float,
        y: float,
        species: SpeciesProfile,
    ) -> tuple[Pot, CareEvent]: ...

    def advance(
        self,
        pot: Pot,
        species: SpeciesProfile,
        events: list[CareEvent],
        now: datetime,
    ) -> Pot: ...

    def timeline(self, profile: PlantingProfile, species: SpeciesProfile) -> list[StageMark]: ...

    def make_event(self, pot_id: str, action: CareAction, now: datetime, note: str = "") -> CareEvent: ...


class CarePort(Protocol):
    def interval_days(self, species: SpeciesProfile, profile: PlantingProfile) -> float: ...

    def plan(
        self,
        pot: Pot,
        species: SpeciesProfile,
        events: list[CareEvent],
        now: datetime,
    ) -> CarePlan: ...


class GroupPort(Protocol):
    def suggest(
        self,
        pots: list[Pot],
        existing: list[CropGroup],
        titles: dict[str, str],
    ) -> tuple[list[CropGroup], list[Pot]]: ...


class ScorePort(Protocol):
    def score_zone(
        self,
        zone: Zone,
        pots: list[Pot],
        events: list[CareEvent],
        nickname: str,
    ) -> FarmScore: ...

    def leaderboard(self, you: FarmScore, friends: list[Friend]) -> list[LeaderboardRow]: ...


class StorePort(Protocol):
    def get_settings(self) -> Settings: ...

    def save_settings(self, settings: Settings) -> None: ...

    def list_zones(self) -> list[Zone]: ...

    def save_zone(self, zone: Zone) -> None: ...

    def delete_zone(self, zone_id: str) -> None: ...

    def list_pots(self, zone_id: str) -> list[Pot]: ...

    def save_pot(self, pot: Pot) -> None: ...

    def list_groups(self, zone_id: str) -> list[CropGroup]: ...

    def save_group(self, group: CropGroup) -> None: ...

    def list_events(self, pot_id: str) -> list[CareEvent]: ...

    def list_zone_events(self, zone_id: str) -> list[CareEvent]: ...

    def add_event(self, event: CareEvent) -> None: ...

    def list_reminders(self, zone_id: str | None = None) -> list[Reminder]: ...

    def save_reminder(self, reminder: Reminder) -> None: ...

    def delete_reminder(self, reminder_id: str) -> None: ...

    def list_friends(self) -> list[Friend]: ...

    def save_friend(self, friend: Friend) -> None: ...


class ReminderPort(Protocol):
    def sync(
        self,
        plans: list[CarePlan],
        alerts: list[WeatherAlert],
        now: datetime,
        zone_id: str,
        notify_water: bool,
        notify_weather: bool,
    ) -> list[Reminder]: ...

    def due(self, now: datetime, zone_id: str | None = None) -> list[Reminder]: ...


class WidgetPort(Protocol):
    def farm(self, now: datetime) -> WidgetSnapshot: ...

    def zone(self, zone_id: str, now: datetime) -> WidgetSnapshot: ...

    def group(self, group_id: str, now: datetime) -> WidgetSnapshot: ...


class GardenCanvas(Protocol):
    """Карта. Оболонка не імпортує папку garden, вона отримує об'єкт з цими методами."""

    def control(self) -> object: ...

    def show(self, view: ZoneView) -> None: ...

    def spawn_point(self) -> tuple[float, float]: ...


MakeCanvas = Callable[
    [Callable[[str], None], Callable[[str, float, float], None]],
    GardenCanvas,
]


class Actions(Protocol):
    """Єдиний вхід для екранів. Оболонка кличе тільки це."""

    def list_zones(self) -> list[Zone]: ...

    def create_zone(self, name: str, kind: ZoneKind, territory: str) -> Zone: ...

    def open_zone(self, zone_id: str) -> ZoneView: ...

    def search_species(self, query: str) -> list[SpeciesProfile]: ...

    def describe(self, name: str, variety: str, soil: SoilType, zone_id: str) -> SpeciesProfile: ...

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
        """planted_at у минулому — посадка, зроблена ще до застосунку. None — зараз (sim_now)."""
        ...

    def move_pot(self, zone_id: str, pot_id: str, x: float, y: float) -> ZoneView: ...

    def water(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        """at — коли полили насправді, якщо записують пізніше. None — зараз (sim_now)."""
        ...

    def fertilize(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView: ...

    def harvest(self, zone_id: str, pot_id: str) -> ZoneView: ...

    def group_crops(self, zone_id: str) -> ZoneView: ...

    def shift_days(self, delta: int) -> int: ...

    def get_settings(self) -> Settings: ...

    def save_settings(self, settings: Settings) -> Settings: ...

    def your_score(self, zone_id: str) -> FarmScore: ...

    def leaderboard(self, zone_id: str) -> list[LeaderboardRow]: ...

    def add_friend(self, nickname: str, points: int) -> list[LeaderboardRow]: ...

    def widgets(self) -> list[WidgetSnapshot]: ...

    def due_reminders(self) -> list[Reminder]: ...
