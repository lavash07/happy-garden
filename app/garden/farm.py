"""Сцена фазенди: фото теплиці зі столом, горщики стоять на стільниці.

Реалізує GardenCanvas (control, show, spawn_point) з тим самим конструктором, що GardenMap.
Додатково має `on_add`: якщо його задати, на вільному місці столу з'являється «+».
Стан рослин не рахує: етап і культуру бере з ZoneView.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.contracts.checks import clamp_world
from app.contracts.constants import SPAWN_GAP, WORLD_SIZE
from app.contracts.labels import BTN_PLANT, STAGE_LABELS
from app.contracts.models import PotCard, ZoneView
from app.contracts.pictures import PICTURE_FOOT, PICTURE_POT_SHARE, PICTURE_RATIO, pot_picture

BACKGROUND = "backgrounds/farm.jpg"  # копія «bg_for site.png», 2560 px
BG_W, BG_H = 2560, 1429

# Стільниця на фото, частки картинки.
TABLE_LEFT, TABLE_RIGHT = 0.08, 0.92
TABLE_FOOT_Y = 0.735  # де стоїть дно горщика

POT_W = 0.24  # ширина кадру горщика від висоти картинки (сам горщик — 0.62 кадру)
MIN_POT_W = 70
GAP = -0.12  # кадри трохи заходять один на один: по боках горщика в кадрі порожньо
PLUS = 64


class FarmBench:
    def __init__(
        self,
        on_select_pot: Callable[[str], None],
        on_move_pot: Callable[[str, float, float], None],
    ) -> None:
        self._on_select_pot = on_select_pot
        self._on_move_pot = on_move_pot  # стіл не перетягує горщики
        self.on_add: Callable[[], None] | None = None
        self._cards: list[PotCard] = []
        self._selected: str | None = None
        self._size = (0.0, 0.0)
        self._layer = ft.Stack(expand=True)
        self._root = ft.Container(
            expand=True,
            on_size_change=self._resized,
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Image(src=BACKGROUND, fit=ft.BoxFit.COVER, left=0, top=0, right=0, bottom=0),
                    self._layer,
                ],
            ),
        )

    # --- GardenCanvas ---

    def control(self) -> ft.Control:
        return self._root

    def show(self, view: ZoneView) -> None:
        self._cards = sorted(view.cards, key=lambda card: (card.pot.x, card.pot.id))
        if self._selected not in {card.pot.id for card in self._cards}:
            self._selected = None
        self._render()

    def spawn_point(self) -> tuple[float, float]:
        """Нові горщики стають праворуч: x росте з кількістю, тож порядок на столі сталий."""
        right = max((card.pot.x for card in self._cards), default=0.0)
        return clamp_world(right + SPAWN_GAP, WORLD_SIZE / 2)

    # --- розкладка ---

    def _resized(self, e: ft.LayoutSizeChangeEvent) -> None:
        size = (float(e.width), float(e.height))
        if size != self._size:
            self._size = size
            self._render()

    def _render(self) -> None:
        width, height = self._size
        if width <= 0 or height <= 0:
            return
        scale = max(width / BG_W, height / BG_H)
        img_w, img_h = BG_W * scale, BG_H * scale
        origin_x, origin_y = (width - img_w) / 2, (height - img_h) / 2

        # Видима частина стільниці: на телефоні фото обрізане з боків.
        left = max(origin_x + TABLE_LEFT * img_w, 12.0)
        right = min(origin_x + TABLE_RIGHT * img_w, width - 12.0)
        foot = origin_y + TABLE_FOOT_Y * img_h

        slots = len(self._cards) + (1 if self.on_add else 0)
        pot_w = POT_W * img_h
        pot_h = pot_w / PICTURE_RATIO
        if slots:
            fit_w = (right - left) / (slots + GAP * (slots - 1))
            if pot_w > fit_w:
                pot_w = max(fit_w, MIN_POT_W)
                pot_h = pot_w / PICTURE_RATIO
        step = pot_w * (1 + GAP)
        row = pot_w + step * (slots - 1) if slots else 0.0
        start = (left + right) / 2 - row / 2 + pot_w / 2  # центр першого місця

        controls: list[ft.Control] = []
        for index, card in enumerate(self._cards):
            controls.extend(self._pot(card, start + index * step, foot, pot_w, pot_h))
        if self.on_add:
            controls.append(self._plus(start + len(self._cards) * step, foot, min(PLUS, pot_w * PICTURE_POT_SHARE)))
        self._layer.controls = controls
        try:
            self._layer.update()
        except Exception:  # noqa: BLE001 — ще не на сторінці, покажеться при додаванні
            pass

    def _pot(self, card: PotCard, cx: float, foot: float, w: float, h: float) -> list[ft.Control]:
        selected = card.pot.id == self._selected
        if selected:
            w, h = w * 1.08, h * 1.08
        shadow_w, shadow_h = w * 0.6, max(w * 0.08, 4)
        picture = pot_picture(card.pot.profile.species_id, card.pot.stage)
        body: ft.Control
        if picture:
            body = ft.Image(src=picture, width=w, height=h, fit=ft.BoxFit.CONTAIN)
        else:
            body = _drawn_pot(card.species.glyph, w, h)
        top = foot - h * PICTURE_FOOT
        label_w = 220
        label = ft.Container(
            left=min(max(cx - label_w / 2, 8.0), self._size[0] - label_w - 8),
            top=foot + 8,
            width=label_w,
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                padding=ft.Padding(10, 3, 10, 3),
                border_radius=12,
                bgcolor="#2E7D32",
                content=ft.Text(
                    f"{card.species.name} · {STAGE_LABELS[card.pot.stage]}",
                    color="#FFFFFF",
                    size=12,
                    weight=ft.FontWeight.W_600,
                    no_wrap=True,
                ),
            ),
        )
        return [
            ft.Container(
                left=cx - shadow_w / 2,
                top=foot - shadow_h / 2,
                width=shadow_w,
                height=shadow_h,
                bgcolor="#000000",
                opacity=0.2,
                border_radius=100,
            ),
            ft.Container(
                left=cx - w / 2,
                top=top,
                width=w,
                height=h,
                on_click=lambda _, pot_id=card.pot.id: self._select(pot_id),
                content=body,
            ),
            *([label] if selected else []),
        ]

    def _plus(self, cx: float, foot: float, size: float) -> ft.Control:
        return ft.Container(
            left=cx - size / 2,
            top=foot - size,
            width=size,
            height=size,
            border_radius=size,
            bgcolor=ft.Colors.with_opacity(0.85, "#FFFFFF"),
            border=ft.Border.all(2, "#2E7D32"),
            shadow=ft.BoxShadow(blur_radius=14, color=ft.Colors.with_opacity(0.25, "#1B2E1B"), offset=ft.Offset(0, 4)),
            tooltip=BTN_PLANT,
            ink=True,
            on_click=lambda _: self.on_add() if self.on_add else None,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.ADD_ROUNDED, color="#2E7D32", size=size * 0.5),
        )

    def _select(self, pot_id: str) -> None:
        self._selected = pot_id
        self._render()
        self._on_select_pot(pot_id)


def _drawn_pot(glyph: str, w: float, h: float) -> ft.Control:
    """Запасний горщик, коли для культури ще немає PNG: глиняний горщик і glyph з довідки."""
    # Розмір як у рендерах render_pots.py: горщик 0.62 ширини кадру, тіло ~0.3 висоти.
    pot_w, pot_h = w * PICTURE_POT_SHARE, h * 0.3
    rim_h = pot_h * 0.18
    return ft.Container(
        width=w,
        height=h,
        content=ft.Column(
            spacing=0,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(glyph or "🌱", size=w * 0.28),
                ft.Container(width=pot_w * 1.06, height=rim_h, bgcolor="#A0533B", border_radius=4),
                ft.Container(
                    width=pot_w,
                    height=pot_h - rim_h,
                    margin=ft.Margin(0, 0, 0, h * (1 - PICTURE_FOOT)),
                    bgcolor="#8E4A35",
                    border_radius=ft.BorderRadius(2, 2, pot_w * 0.18, pot_w * 0.18),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("• ‿ •", size=w * 0.09, color="#2B1A14"),
                ),
            ],
        ),
    )
