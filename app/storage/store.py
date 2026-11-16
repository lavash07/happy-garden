"""SQLite. У колонці data лежить JSON з app.contracts.codec. Див. TASK.md."""

from __future__ import annotations

from pathlib import Path

from app.contracts.models import (
    CareEvent,
    CropGroup,
    Friend,
    Pot,
    Reminder,
    Settings,
    Zone,
)


class GardenStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self.schema = str(Path(__file__).with_name("schema.sql"))

    def get_settings(self) -> Settings:
        raise NotImplementedError("app/storage/store.py")

    def save_settings(self, settings: Settings) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_zones(self) -> list[Zone]:
        raise NotImplementedError("app/storage/store.py")

    def save_zone(self, zone: Zone) -> None:
        raise NotImplementedError("app/storage/store.py")

    def delete_zone(self, zone_id: str) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_pots(self, zone_id: str) -> list[Pot]:
        raise NotImplementedError("app/storage/store.py")

    def save_pot(self, pot: Pot) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_groups(self, zone_id: str) -> list[CropGroup]:
        raise NotImplementedError("app/storage/store.py")

    def save_group(self, group: CropGroup) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_events(self, pot_id: str) -> list[CareEvent]:
        raise NotImplementedError("app/storage/store.py")

    def list_zone_events(self, zone_id: str) -> list[CareEvent]:
        raise NotImplementedError("app/storage/store.py")

    def add_event(self, event: CareEvent) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_reminders(self, zone_id: str | None = None) -> list[Reminder]:
        raise NotImplementedError("app/storage/store.py")

    def save_reminder(self, reminder: Reminder) -> None:
        raise NotImplementedError("app/storage/store.py")

    def delete_reminder(self, reminder_id: str) -> None:
        raise NotImplementedError("app/storage/store.py")

    def list_friends(self) -> list[Friend]:
        raise NotImplementedError("app/storage/store.py")

    def save_friend(self, friend: Friend) -> None:
        raise NotImplementedError("app/storage/store.py")
