"""Картка горщика: етап, настрій, відсотки, полив (останній і наступний), прогноз етапів, календар.

Усе береться з PotCard, яку зібрав фасад. Тут лише показ і виклики actions.water / fertilize / harvest.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import flet as ft

from app.contracts.clock import sim_now
from app.contracts.errors import PotNotFound, ZoneNotFound
from app.contracts.labels import (
    BTN_FERTILIZE,
    BTN_HARVEST,
    BTN_WATER,
    LBL_FERTILITY,
    LBL_HEALTH,
    LBL_MOISTURE,
    LBL_SOIL_QUALITY,
    LBL_TIMELINE,
    LBL_TIPS,
    MOOD_LABELS,
    SOIL_LABELS,
    STAGE_LABELS,
    UNVERIFIED_NOTE,
    as_percent,
)
from app.contracts.lookup import card_for
from app.contracts.models import GrowthStage, Mood, PotCard, ZoneView
from app.contracts.pictures import PICTURE_RATIO, pot_picture
from app.contracts.ports import Actions
from app.shell.dates import day_month, relative, when
from app.shell.theme import CARD, DANGER, GREEN, INFO, MIN_TAP, TEXT, WARNING

SHEET_WIDTH = 460
MOOD_COLORS = {Mood.HAPPY: GREEN, Mood.OK: INFO, Mood.THIRSTY: WARNING, Mood.SAD: DANGER}
WATER_LATER = "Записати полив раніше"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _bar(label: str, value: float, color: str) -> ft.Control:
    return ft.Column(
        spacing=2,
        expand=True,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[ft.Text(label, size=12, color=TEXT), ft.Text(f"{as_percent(value)}%", size=12, color=TEXT)],
            ),
            ft.ProgressBar(value=max(0.0, min(1.0, value)), color=color, bgcolor=ft.Colors.with_opacity(0.12, color), height=6, border_radius=6),
        ],
    )


def _line(icon: ft.IconData, title: str, value: str, color: str = TEXT) -> ft.Control:
    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Icon(icon, size=20, color=GREEN),
            ft.Column(
                tight=True,
                spacing=0,
                expand=True,
                controls=[
                    ft.Text(title, size=12, color=ft.Colors.with_opacity(0.65, TEXT)),
                    ft.Text(value, size=14, color=color, weight=ft.FontWeight.W_600),
                ],
            ),
        ],
    )


def _last_care(next_at: datetime, every_days: float, planted_at: datetime) -> datetime | None:
    """План рахує «наступний = останній + інтервал». Якщо останній — сама посадка, догляду ще не було."""
    last = _utc(next_at) - timedelta(days=every_days)
    return None if abs((last - _utc(planted_at)).total_seconds()) < 60 else last


def pot_sheet(
    actions: Actions,
    zone_id: str,
    card: PotCard,
    on_changed: Callable[[ZoneView], None],
    on_close: Callable[[], None],
) -> ft.Control:
    current = {"card": card}
    body = ft.Column(tight=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    error = ft.Text("", color=DANGER, visible=False)

    def act(call: Callable[[], ZoneView]) -> None:
        try:
            view = call()
        except (ValueError, PotNotFound, ZoneNotFound) as exc:
            error.value = str(exc)
            error.visible = True
            error.update()
            return
        fresh = card_for(view, current["card"].pot.id)
        if fresh is not None:
            current["card"] = fresh
        on_changed(view)
        render()
        body.update()

    def water_earlier(_: ft.Event) -> None:
        now = sim_now(actions.get_settings())
        planted = _utc(current["card"].pot.profile.planted_at)

        def picked(e: ft.Event) -> None:
            value = e.control.value
            if not value:
                return
            day = value.date() if isinstance(value, datetime) else value
            at = datetime(day.year, day.month, day.day, 9).astimezone(timezone.utc)
            act(lambda: actions.water(zone_id, current["card"].pot.id, at))

        body.page.show_dialog(
            ft.DatePicker(
                first_date=planted,
                last_date=now,
                value=now,
                on_change=picked,
                help_text=WATER_LATER,
            )
        )

    def render() -> None:
        c = current["card"]
        pot, species, plan, fc = c.pot, c.species, c.plan, c.forecast
        now = sim_now(actions.get_settings())
        planted = _utc(pot.profile.planted_at)
        mood_color = MOOD_COLORS[pot.mood]

        picture = pot_picture(pot.profile.species_id, pot.stage)
        thumb: ft.Control = (
            ft.Image(src=picture, width=70, height=70 / PICTURE_RATIO, fit=ft.BoxFit.CONTAIN)
            if picture
            else ft.Text(species.glyph, size=44)
        )
        header = ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                thumb,
                ft.Column(
                    tight=True,
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(species.name, size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(f"Сорт: {pot.profile.variety} · {SOIL_LABELS[pot.profile.soil_type]}", size=12, color=ft.Colors.with_opacity(0.7, TEXT)),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Container(
                                    padding=ft.Padding(10, 3, 10, 3),
                                    border_radius=10,
                                    bgcolor=GREEN,
                                    content=ft.Text(STAGE_LABELS[pot.stage], size=12, color=CARD, weight=ft.FontWeight.W_600),
                                ),
                                ft.Container(
                                    padding=ft.Padding(10, 3, 10, 3),
                                    border_radius=10,
                                    bgcolor=ft.Colors.with_opacity(0.12, mood_color),
                                    content=ft.Text(MOOD_LABELS[pot.mood], size=12, color=mood_color, weight=ft.FontWeight.W_600),
                                ),
                            ],
                        ),
                    ],
                ),
                ft.IconButton(ft.Icons.CLOSE_ROUNDED, on_click=lambda _: on_close()),
            ],
        )
        stage_bar = ft.ProgressBar(
            value=pot.stage_progress, color=GREEN, bgcolor=ft.Colors.with_opacity(0.12, GREEN), height=8, border_radius=8
        )

        last_water = _last_care(plan.next_water_at, plan.water_every_days, planted)
        last_feed = _last_care(plan.next_fertilize_at, plan.fertilize_every_days, planted)
        water_due = _utc(plan.next_water_at) <= now
        feed_due = _utc(plan.next_fertilize_at) <= now
        care = [
            _line(ft.Icons.EVENT_ROUNDED, "Посаджено", f"{day_month(planted)} · {relative(planted, now)}"),
            _line(
                ft.Icons.WATER_DROP_ROUNDED,
                "Останній полив",
                when(last_water, now) if last_water else "Ще не поливали",
            ),
            _line(
                ft.Icons.SCHEDULE_ROUNDED,
                f"Наступний полив · раз на {plan.water_every_days:g} дн",
                ("Пора полити — " if water_due else "") + when(plan.next_water_at, now),
                DANGER if water_due else TEXT,
            ),
            _line(
                ft.Icons.SPA_ROUNDED,
                f"Добриво · раз на {plan.fertilize_every_days:g} дн"
                + (f" · було {day_month(last_feed)}" if last_feed else ""),
                ("Пора удобрити — " if feed_due else "") + when(plan.next_fertilize_at, now),
                WARNING if feed_due else TEXT,
            ),
        ]

        if pot.stage == GrowthStage.RIPE:
            prediction = [_line(ft.Icons.AGRICULTURE_ROUNDED, "Прогноз", "Уже стигле — можна збирати", GREEN)]
        elif pot.stage == GrowthStage.HARVESTED or fc is None or fc.next_stage is None:
            prediction = [_line(ft.Icons.AGRICULTURE_ROUNDED, "Прогноз", "Урожай зібрано")]
        else:
            prediction = [
                _line(
                    ft.Icons.TRENDING_UP_ROUNDED,
                    f"Наступний етап: {STAGE_LABELS[fc.next_stage]}",
                    when(fc.next_stage_at, now) if fc.next_stage_at else "—",
                ),
            ]
            if fc.ripe_at and fc.next_stage != GrowthStage.RIPE:
                prediction.append(_line(ft.Icons.EMOJI_NATURE_ROUNDED, "Стигле буде", when(fc.ripe_at, now)))
            prediction.append(
                ft.Text(
                    f"Прогноз за сортом «{pot.profile.variety}» і поточним здоров'ям, приблизний.",
                    size=11,
                    color=ft.Colors.with_opacity(0.6, TEXT),
                )
            )

        timeline = ft.Row(
            wrap=True,
            spacing=6,
            run_spacing=6,
            controls=[
                ft.Container(
                    padding=ft.Padding(8, 3, 8, 3),
                    border_radius=8,
                    bgcolor=GREEN if mark.stage == pot.stage else ft.Colors.with_opacity(0.08, GREEN),
                    content=ft.Text(
                        f"день {mark.starts_on_day} — {mark.label}",
                        size=11,
                        color=CARD if mark.stage == pot.stage else TEXT,
                    ),
                )
                for mark in c.timeline
            ],
        )

        buttons = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.FilledButton(
                    content=ft.Text(BTN_WATER),
                    icon=ft.Icons.WATER_DROP_ROUNDED,
                    bgcolor=INFO,
                    color=CARD,
                    height=MIN_TAP,
                    on_click=lambda _: act(lambda: actions.water(zone_id, pot.id)),
                ),
                ft.FilledButton(
                    content=ft.Text(BTN_FERTILIZE),
                    icon=ft.Icons.SPA_ROUNDED,
                    bgcolor=GREEN,
                    color=CARD,
                    height=MIN_TAP,
                    on_click=lambda _: act(lambda: actions.fertilize(zone_id, pot.id)),
                ),
                *(
                    [
                        ft.FilledButton(
                            content=ft.Text(BTN_HARVEST),
                            icon=ft.Icons.AGRICULTURE_ROUNDED,
                            bgcolor=WARNING,
                            color=CARD,
                            height=MIN_TAP,
                            on_click=lambda _: act(lambda: actions.harvest(zone_id, pot.id)),
                        )
                    ]
                    if pot.stage == GrowthStage.RIPE
                    else []
                ),
                ft.OutlinedButton(
                    content=ft.Text(WATER_LATER),
                    icon=ft.Icons.EDIT_CALENDAR_ROUNDED,
                    height=MIN_TAP,
                    on_click=water_earlier,
                ),
            ],
        )

        body.controls = [
            header,
            stage_bar,
            ft.Row(spacing=12, controls=[_bar(LBL_MOISTURE, pot.moisture, INFO), _bar(LBL_HEALTH, pot.health, GREEN)]),
            ft.Row(
                spacing=12,
                controls=[_bar(LBL_SOIL_QUALITY, pot.soil_quality, WARNING), _bar(LBL_FERTILITY, pot.fertility, GREEN)],
            ),
            ft.Divider(height=1),
            *care,
            ft.Divider(height=1),
            *prediction,
            *(
                [ft.Text(LBL_TIPS, size=13, weight=ft.FontWeight.W_600, color=TEXT), ft.Text(" · ".join(plan.tips), size=12, color=TEXT)]
                if plan.tips
                else []
            ),
            ft.Text(LBL_TIMELINE, size=13, weight=ft.FontWeight.W_600, color=TEXT),
            timeline,
            *([ft.Text(UNVERIFIED_NOTE, size=11, color=WARNING)] if not species.verified else []),
            error,
            buttons,
        ]

    render()

    sheet = ft.Container(
        width=SHEET_WIDTH,
        padding=22,
        border_radius=24,
        bgcolor=ft.Colors.with_opacity(0.97, CARD),
        shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.25, TEXT), offset=ft.Offset(0, 12)),
        content=body,
    )
    return ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        bgcolor=ft.Colors.with_opacity(0.35, TEXT),
        on_click=lambda _: on_close(),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.Container(padding=16, content=ft.GestureDetector(on_tap=lambda _: None, content=sheet))],
        ),
    )
