"""Банер погоди біля назви профілю. Показує найважливіше попередження; тап розгортає решту."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.contracts.models import AlertSeverity, WeatherAlert
from app.shell.theme import CARD, DANGER, INFO, TEXT, WARNING

COLORS = {AlertSeverity.DANGER: DANGER, AlertSeverity.WARNING: WARNING, AlertSeverity.INFO: INFO}
MAX_W = 300
LOADING = "Дивимось погоду…"

# Значок за заголовком попередження з app/knowledge/weather.py.
_ICONS: tuple[tuple[str, ft.IconData], ...] = (
    ("Гроза", ft.Icons.THUNDERSTORM_ROUNDED),
    ("Мороз", ft.Icons.AC_UNIT_ROUNDED),
    ("Сніг", ft.Icons.AC_UNIT_ROUNDED),
    ("Холодно", ft.Icons.DEVICE_THERMOSTAT_ROUNDED),
    ("Спека", ft.Icons.WB_SUNNY_ROUNDED),
    ("вітер", ft.Icons.AIR_ROUNDED),
    ("Дощ", ft.Icons.WATER_DROP_ROUNDED),
    ("спокійна", ft.Icons.WB_CLOUDY_ROUNDED),
)


def _icon(alert: WeatherAlert) -> ft.IconData:
    for word, icon in _ICONS:
        if word in alert.title:
            return icon
    return ft.Icons.CLOUD_OFF_ROUNDED


def _row(alert: WeatherAlert, trailing: ft.Control | None = None) -> ft.Control:
    color = COLORS[alert.severity]
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(_icon(alert), color=color, size=20),
            ft.Column(
                tight=True,
                spacing=0,
                expand=True,
                controls=[
                    ft.Text(alert.title, color=color, size=13, weight=ft.FontWeight.W_700),
                    ft.Text(alert.advice, color=TEXT, size=12),
                ],
            ),
            *([trailing] if trailing else []),
        ],
    )


class WeatherBanner:
    """Стан банера: «завантаження», список попереджень, згорнуто чи розгорнуто."""

    def __init__(self) -> None:
        self._alerts: tuple[WeatherAlert, ...] = ()
        self._open = False
        self._root = ft.Container(
            width=MAX_W,
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=16,
            animate_size=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=self._toggle,
        )
        self.loading()

    def control(self) -> ft.Control:
        return self._root

    def loading(self) -> None:
        self._alerts = ()
        self._open = False
        self._root.bgcolor = ft.Colors.with_opacity(0.85, CARD)
        self._root.border = None
        self._root.content = ft.Row(
            spacing=8,
            controls=[
                ft.ProgressRing(width=14, height=14, stroke_width=2, color=INFO),
                ft.Text(LOADING, size=12, color=ft.Colors.with_opacity(0.7, TEXT)),
            ],
        )

    def show(self, alerts: tuple[WeatherAlert, ...] | list[WeatherAlert]) -> None:
        self._alerts = tuple(alerts)
        if not self._alerts:
            self.loading()
            return
        top = self._alerts[0]
        color = COLORS[top.severity]
        self._root.bgcolor = ft.Colors.with_opacity(0.92, CARD)
        self._root.border = ft.Border.all(1.5, ft.Colors.with_opacity(0.6, color))
        more = len(self._alerts) - 1
        badge: ft.Control | None = None
        if more:
            badge = ft.Container(
                padding=ft.Padding(8, 2, 8, 2),
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.12, color),
                content=ft.Row(
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(f"+{more}", size=12, color=color, weight=ft.FontWeight.W_700),
                        ft.Icon(
                            ft.Icons.EXPAND_LESS_ROUNDED if self._open else ft.Icons.EXPAND_MORE_ROUNDED,
                            size=16,
                            color=color,
                        ),
                    ],
                ),
            )
        rows = [_row(top, badge)]
        if self._open:
            rows.extend(_row(alert) for alert in self._alerts[1:])
        self._root.content = ft.Column(tight=True, spacing=8, controls=rows)

    def _toggle(self, _: ft.Event) -> None:
        if len(self._alerts) < 2:
            return
        self._open = not self._open
        self.show(self._alerts)
        self._root.update()


def poll_alerts(
    load: Callable[[], tuple[WeatherAlert, ...]],
    banner: WeatherBanner,
    still_current: Callable[[], bool],
    tries: int = 40,
    pause_s: float = 0.4,
) -> None:
    """Для фонового потоку: чекати, доки фасад принесе погоду, і оновити банер."""
    import time

    for _ in range(tries):
        if not still_current():
            return
        try:
            alerts = load()
        except Exception:  # noqa: BLE001
            return
        if alerts:
            if still_current():
                banner.show(alerts)
                try:
                    banner.control().update()
                except Exception:  # noqa: BLE001 — екран уже закрили
                    pass
            return
        time.sleep(pause_s)
