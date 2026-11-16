"""Форма посадки: культура, сорт насіння, ґрунт і коли посаджено (сьогодні, дата або етап зараз).

Культури й сорти бере з actions.search_species. Садить через actions.plant(..., planted_at).
Етап → дата посадки рахується за нормативним календарем довідки (ideal_timeline), без формул росту.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import flet as ft

from app.contracts.clock import sim_now
from app.contracts.constants import DEFAULT_VARIETY
from app.contracts.errors import SpeciesNotFound, ZoneNotFound
from app.contracts.labels import (
    BTN_BACK,
    BTN_PLANT,
    LBL_SOIL,
    LBL_SPECIES,
    LBL_VARIETY,
    SOIL_LABELS,
    STAGE_LABELS,
    UNVERIFIED_NOTE,
)
from app.contracts.models import STAGE_ORDER, GrowthStage, SoilType, SpeciesProfile, ZoneView
from app.contracts.ports import Actions
from app.contracts.timeline import ideal_timeline
from app.shell.dates import day_month
from app.shell.theme import CARD, DANGER, GREEN, MIN_TAP, TEXT, WARNING

FORM_WIDTH = 440
LBL_SEEDS = "Сорт насіння"
LBL_WHEN = "Коли посаджено"
WHEN_TODAY, WHEN_DATE, WHEN_STAGE = "today", "date", "stage"
WHEN_LABELS = {WHEN_TODAY: "Сьогодні", WHEN_DATE: "Обрати дату", WHEN_STAGE: "Знаю етап"}
# Щоб обраний етап точно настав: трохи всередину етапу і запас на швидкість росту < 1.
STAGE_INTO = 0.3
STAGE_SLACK = 1.05


def _chip(text: str, active: bool, on_click: Callable[[ft.Event], None], leading: str = "") -> ft.Control:
    return ft.Container(
        height=MIN_TAP - 4,
        padding=ft.Padding(12, 0, 14, 0),
        border_radius=MIN_TAP,
        bgcolor=GREEN if active else ft.Colors.with_opacity(0.08, GREEN),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                *([ft.Text(leading, size=17)] if leading else []),
                ft.Text(text, color=CARD if active else TEXT, weight=ft.FontWeight.W_600, size=13),
            ],
        ),
    )


def _section(title: str) -> ft.Control:
    return ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=TEXT)


def planted_for_stage(species: SpeciesProfile, stage: GrowthStage, now: datetime) -> datetime:
    """Дата посадки, за якої за нормативним календарем горщик зараз на цьому етапі."""
    mark = next(m for m in ideal_timeline(species) if m.stage == stage)
    length = float(species.stage_days.get(stage.value, 0))
    days = (mark.starts_on_day + STAGE_INTO * length) * STAGE_SLACK + 1
    return now - timedelta(days=days)


def plant_form(
    actions: Actions,
    zone_id: str,
    x: float,
    y: float,
    on_done: Callable[[ZoneView], None],
    on_cancel: Callable[[], None],
) -> ft.Control:
    entries: list[SpeciesProfile] = actions.search_species("")
    crops: dict[str, list[SpeciesProfile]] = {}
    for entry in entries:
        crops.setdefault(entry.species_id, []).append(entry)

    def general(species_id: str) -> SpeciesProfile:
        items = crops[species_id]
        return next((s for s in items if s.variety == DEFAULT_VARIETY), items[0])

    def seeds(species_id: str) -> list[SpeciesProfile]:
        return [s for s in crops[species_id] if s.variety != DEFAULT_VARIETY]

    first = next(iter(crops), None)
    state: dict = {
        "crop": first,
        "seed": seeds(first)[0].variety if first and seeds(first) else None,
        "when": WHEN_TODAY,
        "date": None,
        "stage": GrowthStage.SPROUT,
    }

    variety_field = ft.TextField(label=LBL_VARIETY, max_length=40, border_radius=12)
    soil = ft.Dropdown(
        label=LBL_SOIL,
        options=[ft.DropdownOption(key=item.value, text=SOIL_LABELS[item]) for item in SoilType],
        border_radius=12,
        expand=True,
    )
    error = ft.Text("", color=DANGER, visible=False)
    body = ft.Column(tight=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def chosen() -> SpeciesProfile | None:
        crop = state["crop"]
        if crop is None:
            return None
        if state["seed"]:
            return next(s for s in crops[crop] if s.variety == state["seed"])
        return general(crop)

    def set_state(**changes: object) -> None:
        if "crop" in changes:
            crop = changes["crop"]
            changes.setdefault("seed", seeds(crop)[0].variety if seeds(crop) else None)  # type: ignore[arg-type]
            soil.value = general(crop).ideal_soil.value  # type: ignore[arg-type]
        state.update(changes)
        render()
        body.update()

    def pick_date(_: ft.Event) -> None:
        now = sim_now(actions.get_settings())

        def picked(e: ft.Event) -> None:
            value = e.control.value
            if value:
                state["date"] = value.date() if isinstance(value, datetime) else value
                render()
                body.update()

        picker = ft.DatePicker(
            first_date=now - timedelta(days=365),
            last_date=now,
            value=state["date"] or now,
            on_change=picked,
            help_text=LBL_WHEN,
        )
        body.page.show_dialog(picker)

    def planted_at() -> datetime | None:
        now = sim_now(actions.get_settings())
        species = chosen()
        if state["when"] == WHEN_DATE and state["date"]:
            picked: date = state["date"]
            if picked >= now.astimezone().date():
                return None
            return datetime(picked.year, picked.month, picked.day, 12).astimezone(timezone.utc)
        if state["when"] == WHEN_STAGE and species is not None:
            return planted_for_stage(species, state["stage"], now)
        return None

    def render() -> None:
        species = chosen()
        crop = state["crop"]
        controls: list[ft.Control] = [
            ft.Row(controls=[ft.TextButton(BTN_BACK, icon=ft.Icons.ARROW_BACK_ROUNDED, on_click=lambda _: on_cancel())]),
            _section(LBL_SPECIES),
            ft.Row(
                wrap=True,
                spacing=8,
                run_spacing=8,
                controls=[
                    _chip(general(sid).name, sid == crop, lambda _, s=sid: set_state(crop=s), general(sid).glyph)
                    for sid in crops
                ],
            ),
        ]
        if crop and seeds(crop):
            controls += [
                _section(LBL_SEEDS),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _chip(s.variety, s.variety == state["seed"], lambda _, v=s.variety: set_state(seed=v))
                        for s in seeds(crop)
                    ],
                ),
            ]
        else:
            controls.append(variety_field)
        if species is not None:
            ripe_day = next(m.starts_on_day for m in ideal_timeline(species) if m.stage == GrowthStage.RIPE)
            controls += [
                ft.Text(
                    f"{species.tips[0] if species.tips else species.summary} · до стиглості ≈ {ripe_day} днів",
                    size=13,
                    color=ft.Colors.with_opacity(0.75, TEXT),
                ),
                *([ft.Text(UNVERIFIED_NOTE, size=12, color=WARNING)] if not species.verified else []),
            ]
        controls += [
            ft.Row([soil]),
            _section(LBL_WHEN),
            ft.Row(
                wrap=True,
                spacing=8,
                run_spacing=8,
                controls=[
                    _chip(label, key == state["when"], lambda _, k=key: set_state(when=k))
                    for key, label in WHEN_LABELS.items()
                ],
            ),
        ]
        if state["when"] == WHEN_DATE:
            controls.append(
                ft.OutlinedButton(
                    content=ft.Text(day_month(datetime.combine(state["date"], datetime.min.time())) if state["date"] else "Обрати в календарі"),
                    icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
                    height=MIN_TAP,
                    on_click=pick_date,
                )
            )
        if state["when"] == WHEN_STAGE:
            controls.append(
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _chip(STAGE_LABELS[stage], stage == state["stage"], lambda _, st=stage: set_state(stage=st))
                        for stage in STAGE_ORDER
                    ],
                )
            )
        controls += [
            error,
            ft.FilledButton(
                content=ft.Text(BTN_PLANT, size=16, weight=ft.FontWeight.W_600),
                icon=ft.Icons.ADD_ROUNDED,
                bgcolor=GREEN,
                color=CARD,
                height=MIN_TAP + 8,
                on_click=submit,
            ),
        ]
        body.controls = controls

    def submit(_: ft.Event | None = None) -> None:
        species = chosen()
        if species is None:
            return
        variety = state["seed"] or (variety_field.value or "")
        try:
            view = actions.plant(zone_id, species.name, variety, SoilType(soil.value), x, y, planted_at())
        except (ValueError, SpeciesNotFound, ZoneNotFound) as exc:
            error.value = str(exc)
            error.visible = True
            error.update()
            return
        on_done(view)

    if first:
        soil.value = general(first).ideal_soil.value
    render()

    card = ft.Container(
        width=FORM_WIDTH,
        padding=24,
        border_radius=24,
        bgcolor=ft.Colors.with_opacity(0.97, CARD),
        shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.25, TEXT), offset=ft.Offset(0, 12)),
        content=body,
    )

    # Затемнення під карткою; натискання повз картку закриває форму.
    return ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        bgcolor=ft.Colors.with_opacity(0.35, TEXT),
        on_click=lambda _: on_cancel(),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.Container(padding=16, content=ft.GestureDetector(on_tap=lambda _: None, content=card))],
        ),
    )
