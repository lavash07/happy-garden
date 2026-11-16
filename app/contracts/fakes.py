"""Вітрина для екранів. Не агрономія.

Справжні формули тільки в docs/RULES.md і app/core.
Не копіюй цю поведінку в рушій.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from app.contracts.checks import (
    clamp_world,
    clean_friend,
    clean_nickname,
    clean_species_query,
    clean_territory,
    clean_variety,
    clean_zone_name,
)
from app.contracts.clock import sim_now
from app.contracts.errors import PotNotFound, SpeciesNotFound, ZoneNotFound
from app.contracts.ids import new_id
from app.contracts.lookup import card_for
from app.contracts.models import (
    CarePlan,
    FarmScore,
    Friend,
    GrowthStage,
    LeaderboardRow,
    Mood,
    PlantingProfile,
    Pot,
    PotCard,
    Reminder,
    Settings,
    SoilType,
    SpeciesProfile,
    WidgetSnapshot,
    Zone,
    ZoneKind,
    ZoneView,
)
from app.contracts.ranking import sort_leaderboard
from app.contracts.samples import POT_C3, sample_species, sample_zone_view
from app.contracts.timeline import ideal_timeline

_YOU_POINTS = 80


class FakeActions:
    def __init__(self) -> None:
        view = sample_zone_view()
        self.settings = Settings(last_zone_id=view.zone.id)
        self.zones = [view.zone]
        self.pots = [card.pot for card in view.cards]
        self.groups = list(view.groups)
        self.species = sample_species()
        self.friends = [Friend(id="friend-demo", nickname="Марічка", points=120)]
        self._sample_alert = view.alerts[0]
        self._sample_reminder = view.reminders[0]

    def list_zones(self) -> list[Zone]:
        return list(self.zones)

    def create_zone(self, name: str, kind: ZoneKind, territory: str) -> Zone:
        zone = Zone(
            id=new_id(),
            name=clean_zone_name(name),
            kind=kind if isinstance(kind, ZoneKind) else ZoneKind(str(kind)),
            territory=clean_territory(territory, self.settings.territory),
        )
        self.zones.append(zone)
        self.settings = replace(self.settings, last_zone_id=zone.id, territory=zone.territory)
        return zone

    def open_zone(self, zone_id: str) -> ZoneView:
        zone = self._zone(zone_id)
        cards = tuple(self._card(pot) for pot in self.pots if pot.zone_id == zone_id)
        groups = tuple(group for group in self.groups if group.zone_id == zone_id)
        reminders = tuple(item for item in (self._sample_reminder,) if item.zone_id == zone_id)
        return ZoneView(zone=zone, cards=cards, groups=groups, alerts=(self._sample_alert,), reminders=reminders)

    def search_species(self, query: str) -> list[SpeciesProfile]:
        text = clean_species_query(query).casefold()
        if not text:
            return list(self.species)
        return [
            item
            for item in self.species
            if text in item.name.casefold() or text in item.species_id or text in item.variety.casefold()
        ]

    def describe(self, name: str, variety: str, soil: SoilType, zone_id: str) -> SpeciesProfile:
        self._zone(zone_id)
        self._soil(soil)
        found = self.search_species(name)
        if not found:
            raise SpeciesNotFound(name)
        return replace(found[0], variety=clean_variety(variety))

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
        point = clamp_world(x, y)
        zone = self._zone(zone_id)
        profile = PlantingProfile(
            species_id=species.species_id,
            variety=species.variety,
            soil_type=self._soil(soil),
            territory=zone.territory,
            zone_kind=zone.kind,
            planted_at=planted_at or sim_now(self.settings),
        )
        pot = Pot(
            id=new_id(),
            zone_id=zone_id,
            profile=profile,
            x=point[0],
            y=point[1],
            stage=GrowthStage.SPROUT,
            stage_progress=0.0,
            moisture=0.8,
            soil_quality=0.7,
            fertility=0.6,
            health=0.8,
            mood=Mood.OK,
        )
        self.pots.append(pot)
        return self.open_zone(zone_id)

    def move_pot(self, zone_id: str, pot_id: str, x: float, y: float) -> ZoneView:
        point = clamp_world(x, y)
        self._replace(zone_id, pot_id, x=point[0], y=point[1])
        return self.open_zone(zone_id)

    def water(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        self._replace(zone_id, pot_id, moisture=0.95, mood=Mood.HAPPY)
        return self.open_zone(zone_id)

    def fertilize(self, zone_id: str, pot_id: str, at: datetime | None = None) -> ZoneView:
        pot = self._pot(zone_id, pot_id)
        self._replace(zone_id, pot_id, fertility=min(1.0, pot.fertility + 0.25), mood=Mood.HAPPY)
        return self.open_zone(zone_id)

    def harvest(self, zone_id: str, pot_id: str) -> ZoneView:
        """Стрибок стадії тут лише для картинки. Дати і здоров'я рахує core."""
        card = self._require_card(zone_id, pot_id)
        if card.pot.stage != GrowthStage.RIPE:
            return self.open_zone(zone_id)
        if card.species.regrows:
            self._replace(zone_id, pot_id, stage=GrowthStage.FLOWERING, stage_progress=0.0, mood=Mood.HAPPY)
        else:
            self._replace(zone_id, pot_id, stage=GrowthStage.HARVESTED, stage_progress=1.0, mood=Mood.OK)
        return self.open_zone(zone_id)

    def group_crops(self, zone_id: str) -> ZoneView:
        self._zone(zone_id)
        return self.open_zone(zone_id)

    def shift_days(self, delta: int) -> int:
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise ValueError("Зсув днів має бути цілим числом")
        offset = self.settings.debug_day_offset + delta
        self.settings = replace(self.settings, debug_day_offset=offset)
        return offset

    def get_settings(self) -> Settings:
        return self.settings

    def save_settings(self, settings: Settings) -> Settings:
        self.settings = replace(
            settings,
            nickname=clean_nickname(settings.nickname),
            territory=clean_territory(settings.territory),
        )
        return self.settings

    def your_score(self, zone_id: str) -> FarmScore:
        self._zone(zone_id)
        return FarmScore(
            zone_id=zone_id,
            nickname=self.settings.nickname,
            health=0.8,
            ripe_count=1,
            points=_YOU_POINTS,
        )

    def leaderboard(self, zone_id: str) -> list[LeaderboardRow]:
        you = self.your_score(zone_id)
        rows = [LeaderboardRow(nickname=you.nickname, points=you.points, is_you=True)]
        rows.extend(LeaderboardRow(nickname=friend.nickname, points=friend.points, is_you=False) for friend in self.friends)
        return sort_leaderboard(rows)

    def add_friend(self, nickname: str, points: int) -> list[LeaderboardRow]:
        name, score = clean_friend(nickname, points)
        self.friends.append(Friend(id=new_id(), nickname=name, points=score))
        zone_id = self.settings.last_zone_id or self.zones[0].id
        return self.leaderboard(zone_id)

    def widgets(self) -> list[WidgetSnapshot]:
        now = sim_now(self.settings)
        pots = self.pots
        thirsty = sum(1 for pot in pots if pot.mood == Mood.THIRSTY)
        ripe = sum(1 for pot in pots if pot.stage == GrowthStage.RIPE)
        farm = WidgetSnapshot(
            scope="farm",
            scope_id="all",
            title="Уся грядка",
            lines=(f"Горщиків: {len(pots)}", f"Стиглих: {ripe}", f"Хочуть пити: {thirsty}"),
            mood=Mood.OK,
            updated_at=now,
        )
        zone_cards = [
            WidgetSnapshot(
                scope="zone",
                scope_id=zone.id,
                title=zone.name,
                lines=(f"Горщиків: {sum(1 for pot in pots if pot.zone_id == zone.id)}",),
                mood=Mood.OK,
                updated_at=now,
            )
            for zone in self.zones
        ]
        return [farm, *zone_cards]

    def due_reminders(self) -> list[Reminder]:
        return [self._sample_reminder]

    def _zone(self, zone_id: str) -> Zone:
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        raise ZoneNotFound(zone_id)

    def _pot(self, zone_id: str, pot_id: str) -> Pot:
        self._zone(zone_id)
        for pot in self.pots:
            if pot.id == pot_id and pot.zone_id == zone_id:
                return pot
        raise PotNotFound(pot_id)

    def _replace(self, zone_id: str, pot_id: str, **changes: object) -> None:
        current = self._pot(zone_id, pot_id)
        updated = replace(current, **changes)
        self.pots = [updated if pot.id == pot_id else pot for pot in self.pots]

    def _card(self, pot: Pot) -> PotCard:
        species = self._species_for(pot)
        plan = CarePlan(
            pot_id=pot.id,
            water_every_days=species.water_every_days,
            fertilize_every_days=species.fertilize_every_days,
            next_water_at=pot.profile.planted_at + timedelta(days=species.water_every_days),
            next_fertilize_at=pot.profile.planted_at + timedelta(days=species.fertilize_every_days),
            tips=species.tips[:2],
        )
        return PotCard(pot=pot, species=species, plan=plan, timeline=ideal_timeline(species))

    def _species_for(self, pot: Pot) -> SpeciesProfile:
        for item in self.species:
            if item.species_id == pot.profile.species_id:
                return replace(item, variety=pot.profile.variety)
        return self.species[0]

    def _require_card(self, zone_id: str, pot_id: str) -> PotCard:
        self._pot(zone_id, pot_id)
        card = card_for(self.open_zone(zone_id), pot_id)
        if card is None:
            raise PotNotFound(pot_id)
        return card

    def _soil(self, soil: SoilType) -> SoilType:
        if isinstance(soil, SoilType):
            return soil
        return SoilType(str(soil))


DEMO_RIPE_POT = POT_C3
