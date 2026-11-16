"""Нік, місцевість, перемикачі нагадувань, кнопки зсуву днів."""

from __future__ import annotations

import flet as ft

from app.contracts.ports import Actions


def settings_view(actions: Actions, on_back) -> ft.Control:
    raise NotImplementedError("app/shell/settings_page.py — див. TASK.md")
