"""Пан, зум і горщики. Формула екрана — у TASK.md."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.contracts.models import ZoneView


class GardenMap:
    def __init__(
        self,
        on_select_pot: Callable[[str], None],
        on_move_pot: Callable[[str, float, float], None],
    ) -> None:
        self._on_select_pot = on_select_pot
        self._on_move_pot = on_move_pot
        self._view: ZoneView | None = None
        self._camera_ready = False

    def control(self) -> ft.Control:
        raise NotImplementedError("app/garden/map.py control — див. TASK.md")

    def show(self, view: ZoneView) -> None:
        raise NotImplementedError("app/garden/map.py show — див. TASK.md")

    def spawn_point(self) -> tuple[float, float]:
        raise NotImplementedError("app/garden/map.py spawn_point — див. TASK.md")
