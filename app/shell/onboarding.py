"""Перший вхід: нік, назва зони, тип і місцевість. Акаунта на сервері немає — це налаштування і перша зона."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import flet as ft

from app.contracts.checks import clean_nickname
from app.contracts.constants import DEFAULT_TERRITORY
from app.contracts.labels import (
    APP_NAME,
    BTN_BACK,
    BTN_CREATE_ZONE,
    LBL_NICKNAME,
    LBL_TERRITORY,
    LBL_ZONE_KIND,
    LBL_ZONE_NAME,
    SUBTITLE,
    ZONE_LABELS,
)
from app.contracts.models import ZoneKind
from app.contracts.ports import Actions
from app.shell.theme import CARD, DANGER, GREEN, MIN_TAP, TEXT, fill, greenhouse_backdrop

FORM_WIDTH = 420


def onboarding_view(
    actions: Actions,
    on_done: Callable[[], None],
    ask_nickname: bool = True,
    on_cancel: Callable[[], None] | None = None,
) -> ft.Control:
    """Перший вхід (з ніком) або ще одна зона (ask_nickname=False, з кнопкою «Назад»)."""
    settings = actions.get_settings()

    nickname = ft.TextField(
        label=LBL_NICKNAME,
        value="" if ask_nickname else settings.nickname,
        autofocus=ask_nickname,
        visible=ask_nickname,
        max_length=20,
        border_radius=12,
    )
    zone_name = ft.TextField(label=LBL_ZONE_NAME, autofocus=not ask_nickname, max_length=30, border_radius=12)
    territory = ft.TextField(
        label=LBL_TERRITORY,
        value=settings.territory or DEFAULT_TERRITORY,
        max_length=60,
        border_radius=12,
        prefix_icon=ft.Icons.PLACE_OUTLINED,
    )
    kind = ft.Dropdown(
        label=LBL_ZONE_KIND,
        value=ZoneKind.GREENHOUSE.value,
        options=[ft.DropdownOption(key=item.value, text=ZONE_LABELS[item]) for item in ZoneKind],
        border_radius=12,
        expand=True,
    )
    error = ft.Text("", color=DANGER, visible=False)

    def submit(_: ft.Event | None = None) -> None:
        try:
            current = actions.get_settings()
            nick = clean_nickname(nickname.value or "") if ask_nickname else current.nickname
            zone = actions.create_zone(zone_name.value or "", ZoneKind(kind.value), territory.value or "")
            current = actions.get_settings()
            territory_value = zone.territory if ask_nickname else current.territory
            actions.save_settings(replace(current, nickname=nick, territory=territory_value, last_zone_id=zone.id))
        except ValueError as exc:
            error.value = str(exc)
            error.visible = True
            error.update()
            return
        on_done()

    def hide_error(_: ft.Event) -> None:
        if error.visible:
            error.visible = False
            error.update()

    for field in (nickname, zone_name, territory):
        field.on_change = hide_error

    async def to_zone_name(_: ft.Event) -> None:
        await zone_name.focus()

    async def to_territory(_: ft.Event) -> None:
        await territory.focus()

    nickname.on_submit = to_zone_name
    zone_name.on_submit = to_territory
    territory.on_submit = submit

    back = ft.Row(
        visible=on_cancel is not None,
        controls=[
            ft.TextButton(
                BTN_BACK,
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                on_click=lambda _: on_cancel() if on_cancel else None,
            )
        ],
    )

    form = ft.Container(
        width=FORM_WIDTH,
        padding=28,
        border_radius=24,
        bgcolor=ft.Colors.with_opacity(0.92, CARD),
        shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.18, TEXT), offset=ft.Offset(0, 12)),
        content=ft.Column(
            tight=True,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                back,
                ft.Icon(ft.Icons.ECO_ROUNDED, color=GREEN, size=40),
                ft.Text(APP_NAME, size=30, weight=ft.FontWeight.BOLD, color=TEXT, text_align=ft.TextAlign.CENTER),
                ft.Text(SUBTITLE, size=15, color=ft.Colors.with_opacity(0.7, TEXT), text_align=ft.TextAlign.CENTER),
                ft.Container(height=4),
                nickname,
                zone_name,
                ft.Row([kind]),
                territory,
                error,
                ft.FilledButton(
                    content=ft.Text(BTN_CREATE_ZONE, size=16, weight=ft.FontWeight.W_600),
                    icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                    bgcolor=GREEN,
                    color=CARD,
                    height=MIN_TAP + 8,
                    on_click=submit,
                ),
            ],
        ),
    )

    return ft.Stack(
        expand=True,
        controls=[
            *greenhouse_backdrop(blur=24, clear_center=False, veil=0.2),
            fill(
                ft.SafeArea(
                    content=ft.Column(
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[ft.Container(content=form, padding=16)],
                    )
                )
            ),
        ],
    )
