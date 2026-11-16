"""Короткі картки стану з уже збережених горщиків. Нових формул тут немає."""

from __future__ import annotations

from datetime import datetime

from app.contracts.models import WidgetSnapshot
from app.storage.store import GardenStore


class WidgetBoard:
    def __init__(self, store: GardenStore) -> None:
        self.store = store

    def farm(self, now: datetime) -> WidgetSnapshot:
        raise NotImplementedError("app/storage/widgets.py farm — див. TASK.md")

    def zone(self, zone_id: str, now: datetime) -> WidgetSnapshot:
        raise NotImplementedError("app/storage/widgets.py zone — див. TASK.md")

    def group(self, group_id: str, now: datetime) -> WidgetSnapshot:
        raise NotImplementedError("app/storage/widgets.py group — див. TASK.md")
