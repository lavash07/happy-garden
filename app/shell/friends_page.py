"""Таблиця очок. Рахує її actions.leaderboard, не цей файл."""

from __future__ import annotations

import flet as ft

from app.contracts.ports import Actions


def friends_view(actions: Actions, zone_id: str, on_back) -> ft.Control:
    raise NotImplementedError("app/shell/friends_page.py — див. TASK.md")
