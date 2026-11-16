"""JSON для бази. Сховище кладе ці рядки як є і не вигадує власні колонки полів."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.contracts.models import (
    STAGE_ORDER,
    CareAction,
    CareEvent,
    CarePlan,
    Category,
    CropGroup,
    Friend,
    GrowthStage,
    Mood,
    PlantingProfile,
    Pot,
    Reminder,
    Settings,
    SoilType,
    SpeciesProfile,
    Zone,
    ZoneKind,
)

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_SPECIES_ID = re.compile(r"^[a-z0-9_]+$")

_SPECIES_FIELDS = (
    "species_id",
    "name",
    "variety",
    "category",
    "glyph",
    "color_hex",
    "regrows",
    "verified",
    "stage_days",
    "ideal_soil",
    "soil_ph",
    "temp_c",
    "water_every_days",
    "fertilize_every_days",
    "summary",
    "tips",
    "sources",
)


def _dump_dt(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _load_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pair(value: object, field: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field}: потрібні два числа")
    return float(value[0]), float(value[1])


def species_from_dict(data: dict) -> SpeciesProfile:
    missing = [key for key in _SPECIES_FIELDS if key not in data]
    if missing:
        raise ValueError("SpeciesProfile бракує полів: " + ", ".join(missing))
    species_id = str(data["species_id"])
    if not _SPECIES_ID.match(species_id):
        raise ValueError("species_id: латиниця, цифри і підкреслення")
    color = str(data["color_hex"])
    if not _COLOR.match(color):
        raise ValueError("color_hex: формат #RRGGBB")
    raw_days = data["stage_days"]
    if not isinstance(raw_days, dict):
        raise ValueError("stage_days: словник етап → дні")
    expected = {stage.value for stage in STAGE_ORDER}
    if set(raw_days) != expected:
        raise ValueError("stage_days має містити рівно: " + ", ".join(stage.value for stage in STAGE_ORDER))
    stage_days = {key: int(raw_days[key]) for key in raw_days}
    if any(days < 0 for days in stage_days.values()):
        raise ValueError("stage_days: дні не від'ємні")
    water = float(data["water_every_days"])
    fertilize = float(data["fertilize_every_days"])
    if water <= 0 or fertilize <= 0:
        raise ValueError("інтервали поливу і добрива мають бути більші за 0")
    tips = data["tips"] if isinstance(data["tips"], list) else None
    sources = data["sources"] if isinstance(data["sources"], list) else None
    if tips is None or sources is None:
        raise ValueError("tips і sources — списки рядків")
    return SpeciesProfile(
        species_id=species_id,
        name=str(data["name"]).strip(),
        variety=str(data["variety"]).strip(),
        category=Category(str(data["category"])),
        glyph=str(data["glyph"]),
        color_hex=color,
        regrows=bool(data["regrows"]),
        verified=bool(data["verified"]),
        stage_days=stage_days,
        ideal_soil=SoilType(str(data["ideal_soil"])),
        soil_ph=_pair(data["soil_ph"], "soil_ph"),
        temp_c=_pair(data["temp_c"], "temp_c"),
        water_every_days=water,
        fertilize_every_days=fertilize,
        summary=str(data["summary"]),
        tips=tuple(str(item) for item in tips),
        sources=tuple(str(item) for item in sources),
    )


def species_to_dict(species: SpeciesProfile) -> dict:
    return {
        "species_id": species.species_id,
        "name": species.name,
        "variety": species.variety,
        "category": species.category.value,
        "glyph": species.glyph,
        "color_hex": species.color_hex,
        "regrows": species.regrows,
        "verified": species.verified,
        "stage_days": dict(species.stage_days),
        "ideal_soil": species.ideal_soil.value,
        "soil_ph": [species.soil_ph[0], species.soil_ph[1]],
        "temp_c": [species.temp_c[0], species.temp_c[1]],
        "water_every_days": species.water_every_days,
        "fertilize_every_days": species.fertilize_every_days,
        "summary": species.summary,
        "tips": list(species.tips),
        "sources": list(species.sources),
    }


def _profile_to_dict(profile: PlantingProfile) -> dict:
    return {
        "species_id": profile.species_id,
        "variety": profile.variety,
        "soil_type": profile.soil_type.value,
        "territory": profile.territory,
        "zone_kind": profile.zone_kind.value,
        "planted_at": _dump_dt(profile.planted_at),
    }


def _profile_from_dict(data: dict) -> PlantingProfile:
    return PlantingProfile(
        species_id=str(data["species_id"]),
        variety=str(data["variety"]),
        soil_type=SoilType(str(data["soil_type"])),
        territory=str(data["territory"]),
        zone_kind=ZoneKind(str(data["zone_kind"])),
        planted_at=_load_dt(str(data["planted_at"])),
    )


def pot_to_dict(pot: Pot) -> dict:
    return {
        "id": pot.id,
        "zone_id": pot.zone_id,
        "profile": _profile_to_dict(pot.profile),
        "x": pot.x,
        "y": pot.y,
        "stage": pot.stage.value,
        "stage_progress": pot.stage_progress,
        "moisture": pot.moisture,
        "soil_quality": pot.soil_quality,
        "fertility": pot.fertility,
        "health": pot.health,
        "mood": pot.mood.value,
        "group_id": pot.group_id,
    }


def pot_from_dict(data: dict) -> Pot:
    group_id = data.get("group_id")
    return Pot(
        id=str(data["id"]),
        zone_id=str(data["zone_id"]),
        profile=_profile_from_dict(data["profile"]),
        x=float(data["x"]),
        y=float(data["y"]),
        stage=GrowthStage(str(data["stage"])),
        stage_progress=float(data["stage_progress"]),
        moisture=float(data["moisture"]),
        soil_quality=float(data["soil_quality"]),
        fertility=float(data["fertility"]),
        health=float(data["health"]),
        mood=Mood(str(data["mood"])),
        group_id=None if group_id in (None, "") else str(group_id),
    )


def zone_to_dict(zone: Zone) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "kind": zone.kind.value,
        "territory": zone.territory,
    }


def zone_from_dict(data: dict) -> Zone:
    return Zone(
        id=str(data["id"]),
        name=str(data["name"]),
        kind=ZoneKind(str(data["kind"])),
        territory=str(data["territory"]),
    )


def group_to_dict(group: CropGroup) -> dict:
    return {
        "id": group.id,
        "zone_id": group.zone_id,
        "species_id": group.species_id,
        "title": group.title,
        "pot_ids": list(group.pot_ids),
        "x": group.x,
        "y": group.y,
    }


def group_from_dict(data: dict) -> CropGroup:
    return CropGroup(
        id=str(data["id"]),
        zone_id=str(data["zone_id"]),
        species_id=str(data["species_id"]),
        title=str(data["title"]),
        pot_ids=tuple(str(item) for item in data["pot_ids"]),
        x=float(data["x"]),
        y=float(data["y"]),
    )


def event_to_dict(event: CareEvent) -> dict:
    return {
        "id": event.id,
        "pot_id": event.pot_id,
        "action": event.action.value,
        "at": _dump_dt(event.at),
        "note": event.note,
    }


def event_from_dict(data: dict) -> CareEvent:
    return CareEvent(
        id=str(data["id"]),
        pot_id=str(data["pot_id"]),
        action=CareAction(str(data["action"])),
        at=_load_dt(str(data["at"])),
        note=str(data.get("note", "")),
    )


def reminder_to_dict(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "zone_id": reminder.zone_id,
        "pot_id": reminder.pot_id,
        "kind": reminder.kind,
        "fire_at": _dump_dt(reminder.fire_at),
        "title": reminder.title,
        "body": reminder.body,
        "done": reminder.done,
    }


def reminder_from_dict(data: dict) -> Reminder:
    pot_id = data.get("pot_id")
    return Reminder(
        id=str(data["id"]),
        zone_id=str(data["zone_id"]),
        pot_id=None if pot_id in (None, "") else str(pot_id),
        kind=str(data["kind"]),
        fire_at=_load_dt(str(data["fire_at"])),
        title=str(data["title"]),
        body=str(data["body"]),
        done=bool(data.get("done", False)),
    )


def settings_to_dict(settings: Settings) -> dict:
    return {
        "nickname": settings.nickname,
        "territory": settings.territory,
        "language": settings.language,
        "notify_water": settings.notify_water,
        "notify_weather": settings.notify_weather,
        "last_zone_id": settings.last_zone_id,
        "debug_day_offset": settings.debug_day_offset,
    }


def settings_from_dict(data: dict | None) -> Settings:
    raw = data or {}
    base = Settings()
    last = raw.get("last_zone_id", base.last_zone_id)
    return Settings(
        nickname=str(raw.get("nickname", base.nickname)),
        territory=str(raw.get("territory", base.territory)),
        language=str(raw.get("language", base.language)),
        notify_water=bool(raw.get("notify_water", base.notify_water)),
        notify_weather=bool(raw.get("notify_weather", base.notify_weather)),
        last_zone_id=None if last in (None, "") else str(last),
        debug_day_offset=int(raw.get("debug_day_offset", base.debug_day_offset)),
    )


def friend_to_dict(friend: Friend) -> dict:
    return {"id": friend.id, "nickname": friend.nickname, "points": friend.points}


def friend_from_dict(data: dict) -> Friend:
    return Friend(id=str(data["id"]), nickname=str(data["nickname"]), points=int(data["points"]))


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def load(raw: str) -> dict:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("очікувався JSON-об'єкт")
    return parsed


def plan_to_dict(plan: CarePlan) -> dict:
    return {
        "pot_id": plan.pot_id,
        "water_every_days": plan.water_every_days,
        "fertilize_every_days": plan.fertilize_every_days,
        "next_water_at": _dump_dt(plan.next_water_at),
        "next_fertilize_at": _dump_dt(plan.next_fertilize_at),
        "tips": list(plan.tips),
    }


def plan_from_dict(data: dict) -> CarePlan:
    tips = data.get("tips", [])
    return CarePlan(
        pot_id=str(data["pot_id"]),
        water_every_days=float(data["water_every_days"]),
        fertilize_every_days=float(data["fertilize_every_days"]),
        next_water_at=_load_dt(str(data["next_water_at"])),
        next_fertilize_at=_load_dt(str(data["next_fertilize_at"])),
        tips=tuple(str(item) for item in tips),
    )
