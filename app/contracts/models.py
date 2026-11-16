"""Спільні дані. Поля додаються тільки тут, і тільки людиною, яка веде ядро."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.contracts.constants import DEFAULT_NICKNAME, DEFAULT_TERRITORY


class ZoneKind(str, Enum):
    GREENHOUSE = "greenhouse"
    GARDEN = "garden"
    FARM = "farm"


class Category(str, Enum):
    VEGETABLE = "vegetable"
    FRUIT = "fruit"


class SoilType(str, Enum):
    CHERNOZEM = "chernozem"
    LOAM = "loam"
    SAND = "sand"
    PEAT = "peat"
    CLAY = "clay"


class GrowthStage(str, Enum):
    SPROUT = "sprout"
    GROWING = "growing"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    RIPE = "ripe"
    HARVESTED = "harvested"


class Mood(str, Enum):
    HAPPY = "happy"
    OK = "ok"
    THIRSTY = "thirsty"
    SAD = "sad"


class CareAction(str, Enum):
    PLANT = "plant"
    WATER = "water"
    FERTILIZE = "fertilize"
    HARVEST = "harvest"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


STAGE_ORDER: tuple[GrowthStage, ...] = (
    GrowthStage.SPROUT,
    GrowthStage.GROWING,
    GrowthStage.FLOWERING,
    GrowthStage.FRUITING,
    GrowthStage.RIPE,
)


def profile_key(species_id: str, variety: str) -> str:
    return f"{species_id.strip().casefold()}:{variety.strip().casefold()}"


@dataclass(frozen=True)
class SpeciesProfile:
    species_id: str
    name: str
    variety: str
    category: Category
    glyph: str
    color_hex: str
    regrows: bool
    verified: bool
    stage_days: dict[str, int]
    ideal_soil: SoilType
    soil_ph: tuple[float, float]
    temp_c: tuple[float, float]
    water_every_days: float
    fertilize_every_days: float
    summary: str
    tips: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_days", dict(self.stage_days))
        object.__setattr__(self, "tips", tuple(self.tips))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "soil_ph", (float(self.soil_ph[0]), float(self.soil_ph[1])))
        object.__setattr__(self, "temp_c", (float(self.temp_c[0]), float(self.temp_c[1])))

    @property
    def key(self) -> str:
        return profile_key(self.species_id, self.variety)


@dataclass(frozen=True)
class PlantingProfile:
    species_id: str
    variety: str
    soil_type: SoilType
    territory: str
    zone_kind: ZoneKind
    planted_at: datetime


@dataclass(frozen=True)
class Pot:
    id: str
    zone_id: str
    profile: PlantingProfile
    x: float
    y: float
    stage: GrowthStage
    stage_progress: float
    moisture: float
    soil_quality: float
    fertility: float
    health: float
    mood: Mood
    group_id: str | None = None


@dataclass(frozen=True)
class CropGroup:
    id: str
    zone_id: str
    species_id: str
    title: str
    pot_ids: tuple[str, ...]
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "pot_ids", tuple(self.pot_ids))


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    kind: ZoneKind
    territory: str


@dataclass(frozen=True)
class CareEvent:
    id: str
    pot_id: str
    action: CareAction
    at: datetime
    note: str = ""


@dataclass(frozen=True)
class CarePlan:
    pot_id: str
    water_every_days: float
    fertilize_every_days: float
    next_water_at: datetime
    next_fertilize_at: datetime
    tips: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tips", tuple(self.tips))


@dataclass(frozen=True)
class StageMark:
    stage: GrowthStage
    starts_on_day: int
    label: str


@dataclass(frozen=True)
class WeatherAlert:
    severity: AlertSeverity
    title: str
    advice: str
    starts_at: datetime
    ends_at: datetime | None = None


@dataclass(frozen=True)
class FarmScore:
    zone_id: str
    nickname: str
    health: float
    ripe_count: int
    points: int


@dataclass(frozen=True)
class Reminder:
    id: str
    zone_id: str
    pot_id: str | None
    kind: str
    fire_at: datetime
    title: str
    body: str
    done: bool = False


@dataclass(frozen=True)
class WidgetSnapshot:
    scope: str
    scope_id: str
    title: str
    lines: tuple[str, ...]
    mood: Mood
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "lines", tuple(self.lines))


@dataclass(frozen=True)
class Settings:
    nickname: str = DEFAULT_NICKNAME
    territory: str = DEFAULT_TERRITORY
    language: str = "uk"
    notify_water: bool = True
    notify_weather: bool = True
    last_zone_id: str | None = None
    debug_day_offset: int = 0


@dataclass(frozen=True)
class Friend:
    id: str
    nickname: str
    points: int


@dataclass(frozen=True)
class LeaderboardRow:
    nickname: str
    points: int
    is_you: bool


@dataclass(frozen=True)
class GrowthForecast:
    """Прогноз етапів з поточного стану. Рахує app/core/forecast.py, формула — docs/RULES.md.

    Наближення: здоров'я лишається як зараз. None — такого етапу вже не буде (стиглий або зібраний).
    """

    next_stage: GrowthStage | None
    next_stage_at: datetime | None
    ripe_at: datetime | None


@dataclass(frozen=True)
class PotCard:
    """Усе, що екран показує по одному горщику. Збирає лише фасад дій."""

    pot: Pot
    species: SpeciesProfile
    plan: CarePlan
    timeline: tuple[StageMark, ...] = ()
    forecast: GrowthForecast | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeline", tuple(self.timeline))


@dataclass(frozen=True)
class ZoneView:
    """Готовий зріз однієї зони. Екран малює його і нічого не перераховує."""

    zone: Zone
    cards: tuple[PotCard, ...]
    groups: tuple[CropGroup, ...]
    alerts: tuple[WeatherAlert, ...]
    reminders: tuple[Reminder, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cards", tuple(self.cards))
        object.__setattr__(self, "groups", tuple(self.groups))
        object.__setattr__(self, "alerts", tuple(self.alerts))
        object.__setattr__(self, "reminders", tuple(self.reminders))
