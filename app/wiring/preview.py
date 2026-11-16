"""Тимчасовий фасад, поки база (людина 5) не готова. Дані в пам'яті, але рахує справжній рушій.

- Культури й сорти — з species.json (find як у app/knowledge/TASK.md: сорт, інакше загальний запис).
- Стан горщика — GrowthEngine.advance з журналу подій на sim_now, план — CarePlanner, прогноз — core.forecast.
- Посадка в минулому отримує припущені поливи (docs/RULES.md, «Посадка в минулому»).
- Погода не блокує екран: open_zone віддає кеш, свіжий прогноз тягне фоновий потік.
  Попередження для кожної культури зони без повторів за парою «рівень + заголовок» (ARCHITECTURE, крок 6).

Коли GardenActions запрацює з базою, main.py перейде на нього; логіку open_zone звідси можна перенести.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from app.contracts.checks import clamp_world, clean_species_query, clean_variety
from app.contracts.clock import real_now, sim_now
from app.contracts.codec import species_from_dict
from app.contracts.constants import DEFAULT_VARIETY, MAX_SIM_DAYS
from app.contracts.errors import PotNotFound, SpeciesNotFound
from app.contracts.fakes import FakeActions
from app.contracts.models import (
    AlertSeverity,
    CareAction,
    CareEvent,
    GrowthStage,
    PlantingProfile,
    Pot,
    PotCard,
    Settings,
    SoilType,
    SpeciesProfile,
    WeatherAlert,
    ZoneView,
)
from app.core.care import CarePlanner, water_interval_days
from app.core.forecast import forecast
from app.core.growth import GrowthEngine
from app.core.timeutil import as_utc
from app.knowledge.catalog import FarmingCatalog
from app.knowledge.weather import CALM_TITLE, WeatherService

ALERTS_TTL_S = 10 * 60
ASSUMED_NOTE = "припущено"
_ORDER = {AlertSeverity.DANGER: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}


def load_species(path: str | None = None) -> list[SpeciesProfile]:
    """Культури з species.json, поки FarmingCatalog.search не реалізований."""
    raw = json.loads(Path(path or FarmingCatalog().path).read_text(encoding="utf-8"))
    return [species_from_dict(item) for item in raw["species"]]


def merge_alerts(groups: list[list[WeatherAlert]]) -> tuple[WeatherAlert, ...]:
    """Унікальні за (рівень, заголовок), найнебезпечніші першими. «Спокійно» — лише коли більше нічого."""
    seen: dict[tuple[AlertSeverity, str], WeatherAlert] = {}
    for alerts in groups:
        for alert in alerts:
            seen.setdefault((alert.severity, alert.title), alert)
    merged = sorted(seen.values(), key=lambda a: _ORDER[a.severity])
    real = [a for a in merged if a.title != CALM_TITLE]
    return tuple(real or merged[:1])


def assumed_waterings(pot: Pot, species: SpeciesProfile, until: datetime, engine: GrowthEngine) -> list[CareEvent]:
    """Поливи кожні interval/2 від посадки до запису: до застосунку рослину доглядали."""
    step = timedelta(days=water_interval_days(species, pot.profile) / 2)
    start = as_utc(pot.profile.planted_at)
    limit = min(as_utc(until), start + timedelta(days=MAX_SIM_DAYS))
    events: list[CareEvent] = []
    at = start + step
    while at < limit:
        events.append(engine.make_event(pot.id, CareAction.WATER, at, ASSUMED_NOTE))
        at += step
    return events


class PreviewActions(FakeActions):
    """Порожній старт (видно екран входу), сорти з довідки, справжній ріст і погода з Open-Meteo."""

    def __init__(self, weather: WeatherService | None = None) -> None:
        super().__init__()
        self.zones.clear()
        self.pots.clear()
        self.groups.clear()
        self.settings = Settings()
        self.species = load_species()
        self.events: list[CareEvent] = []
        self._engine = GrowthEngine()
        self._care = CarePlanner()
        self._weather = weather or WeatherService()
        self._alerts: dict[str, tuple[float, tuple[WeatherAlert, ...]]] = {}
        self._loading: set[str] = set()
        self._lock = threading.Lock()

    # --- довідка ---

    def _find(self, name_or_id: str, variety: str | None = None) -> SpeciesProfile:
        """Як FarmingCatalog.find: збіг за id чи назвою, потрібний сорт або загальний запис з цим сортом."""
        text = clean_species_query(name_or_id).casefold()
        matches = [s for s in self.species if text in (s.species_id, s.name.casefold())]
        if not matches:
            raise SpeciesNotFound(name_or_id)
        wanted = clean_variety(variety or "")
        exact = next((s for s in matches if s.variety.casefold() == wanted.casefold()), None)
        if exact:
            return exact
        general = next((s for s in matches if s.variety == DEFAULT_VARIETY), matches[0])
        return replace(general, variety=wanted)

    def describe(self, name: str, variety: str, soil: SoilType, zone_id: str) -> SpeciesProfile:
        self._zone(zone_id)
        self._soil(soil)
        return self._find(name, variety)

    def _species_for(self, pot: Pot) -> SpeciesProfile:
        return self._find(pot.profile.species_id, pot.profile.variety)

    # --- дії з горщиками ---

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
        species = self.describe(name, variety, soil, zone_id)
        zone = self._zone(zone_id)
        now = sim_now(self.settings)
        when = min(as_utc(planted_at), now) if planted_at else now
        profile = PlantingProfile(
            species_id=species.species_id,
            variety=species.variety,
            soil_type=self._soil(soil),
            territory=zone.territory,
            zone_kind=zone.kind,
            planted_at=when,
        )
        point = clamp_world(x, y)
        pot, event = self._engine.plant(zone_id, profile, point[0], point[1], species)
        self.pots.append(pot)
        self.events.append(event)
        if now - when > timedelta(hours=1):
            self.events.extend(assumed_waterings(pot, species, now, self._engine))
        return self.open_zone(zone_id)

    def water(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        return self._log(zone_id, pot_id, CareAction.WATER, at)

    def fertilize(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        return self._log(zone_id, pot_id, CareAction.FERTILIZE, at)

    def harvest(self, zone_id: str, pot_id: str) -> ZoneView:
        """Збір пишемо лише для стиглого горщика, інакше подія дала б очки ні за що (app/core/NOTES.md)."""
        card = next((c for c in self.open_zone(zone_id).cards if c.pot.id == pot_id), None)
        if card is None:
            raise PotNotFound(pot_id)
        if card.pot.stage != GrowthStage.RIPE:
            return self.open_zone(zone_id)
        return self._log(zone_id, pot_id, CareAction.HARVEST, None)

    def _log(self, zone_id: str, pot_id: str, action: CareAction, at: datetime | None) -> ZoneView:
        pot = self._pot(zone_id, pot_id)
        now = sim_now(self.settings)
        when = now if at is None else min(max(as_utc(at), as_utc(pot.profile.planted_at)), now)
        self.events.append(self._engine.make_event(pot_id, action, when))
        return self.open_zone(zone_id)

    # --- зріз зони ---

    def open_zone(self, zone_id: str) -> ZoneView:
        zone = self._zone(zone_id)
        now = sim_now(self.settings)
        cards: list[PotCard] = []
        updated: dict[str, Pot] = {}
        for pot in (p for p in self.pots if p.zone_id == zone_id):
            species = self._species_for(pot)
            events = [e for e in self.events if e.pot_id == pot.id]
            state = self._engine.advance(pot, species, events, now)
            updated[pot.id] = state
            cards.append(
                PotCard(
                    pot=state,
                    species=species,
                    plan=self._care.plan(state, species, events, now),
                    timeline=self._engine.timeline(state.profile, species),
                    forecast=forecast(state, species, now),
                )
            )
        self.pots = [updated.get(p.id, p) for p in self.pots]
        view = ZoneView(
            zone=zone,
            cards=tuple(cards),
            groups=tuple(g for g in self.groups if g.zone_id == zone_id),
            alerts=(),
            reminders=(),
        )
        return replace(view, alerts=self._cached_alerts(view))

    # --- погода у фоні ---

    def _key(self, view: ZoneView) -> str:
        crops = sorted({card.species.species_id for card in view.cards})
        return f"{view.zone.id}|{view.zone.territory}|{','.join(crops)}"

    def _cached_alerts(self, view: ZoneView) -> tuple[WeatherAlert, ...]:
        key = self._key(view)
        with self._lock:
            cached = self._alerts.get(key)
            fresh = cached is not None and time.monotonic() - cached[0] < ALERTS_TTL_S
            if not fresh and key not in self._loading:
                self._loading.add(key)
                threading.Thread(target=self._fetch, args=(key, view), daemon=True).start()
        return cached[1] if cached else ()

    def _fetch(self, key: str, view: ZoneView) -> None:
        now = real_now()  # погода завжди за справжнім сьогодні, не за «+1 день»
        crops: list[SpeciesProfile | None] = list({card.species.species_id: card.species for card in view.cards}.values())
        try:
            groups = [self._weather.alerts(view.zone.territory, crop, now) for crop in (crops or [None])]  # type: ignore[arg-type]
            alerts = merge_alerts(groups)
        except Exception:  # noqa: BLE001 — погода не має валити фасад
            alerts = ()
        with self._lock:
            self._loading.discard(key)
            if alerts:
                self._alerts[key] = (time.monotonic(), alerts)
