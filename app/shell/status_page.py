"""Картки стану ферми і зон. Тексти вже всередині WidgetSnapshot."""

from __future__ import annotations

import flet as ft

from app.contracts.ports import Actions


def status_view(actions: Actions, on_back) -> ft.Control:
    raise NotImplementedError("app/shell/status_page.py — див. TASK.md")
