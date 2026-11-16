"""Нагадування з уже порахованих планів і погодних попереджень. Див. TASK.md."""

from __future__ import annotations

from datetime import datetime

from app.contracts.models import CarePlan, Reminder, WeatherAlert
from app.storage.store import GardenStore


class ReminderService:
    def __init__(self, store: GardenStore) -> None:
        self.store = store

    def sync(
        self,
        plans: list[CarePlan],
        alerts: list[WeatherAlert],
        now: datetime,
        zone_id: str,
        notify_water: bool,
        notify_weather: bool,
    ) -> list[Reminder]:
        raise NotImplementedError("app/storage/reminders.py sync — див. TASK.md")

    def due(self, now: datetime, zone_id: str | None = None) -> list[Reminder]:
        raise NotImplementedError("app/storage/reminders.py due — див. TASK.md")
