"""Збирає екрани. Сцену зони отримує ззовні (make_canvas) і не імпортує app.garden."""

from __future__ import annotations

import time
from collections.abc import Callable

import flet as ft

from app.contracts.errors import ZoneNotFound
from app.contracts.labels import APP_NAME, BTN_BACK, EMPTY_POTS, ZONE_LABELS
from app.contracts.models import Zone, ZoneKind
from app.contracts.ports import Actions, MakeCanvas
from app.shell.home import home_view
from app.shell.onboarding import onboarding_view
from app.shell.theme import BG, CARD, GREEN, TEXT, fill
from app.shell.zone_page import zone_view

FARM_BG = "backgrounds/farm.jpg"  # те саме фото, що під столом FarmBench

# Зони, для яких уже є сцена (стіл із горщиками). Інші поки відкривають заглушку.
SCENE_KINDS = {ZoneKind.FARM}

ZOOM_MS = 700
# Точка, до якої «летимо»: стіл у колі меню і стіл на сцені.
MENU_FOCUS = ft.Alignment(0, 0.1)
TABLE_FOCUS = ft.Alignment(0, 0.45)
# Сцена у фоні меню «здалеку»: зменшена від цієї точки й розчинена по краях.
MENU_SCENE_SCALE = 0.62
MENU_SCENE_PIVOT = ft.Alignment(0, -0.5)


def _far_center() -> ft.Alignment:
    """Центр зменшеної сцени: точка опори плюс зсув від масштабу."""
    pivot = MENU_SCENE_PIVOT.y
    return ft.Alignment(0, pivot * (1 - MENU_SCENE_SCALE))


def _pick_zone(actions: Actions) -> Zone | None:
    """Зона одна — вона. Кілька — last_zone_id, інакше перша."""
    zones = actions.list_zones()
    if not zones:
        return None
    last = actions.get_settings().last_zone_id
    return next((zone for zone in zones if zone.id == last), zones[0])


def _zone_stub(zone: Zone, pots: int, on_back: Callable[[], None]) -> ft.Control:
    """Тимчасовий екран для теплиці й городу, поки для них немає сцени."""
    return ft.Container(
        expand=True,
        bgcolor=CARD,
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.TextButton(BTN_BACK, icon=ft.Icons.ARROW_BACK_ROUNDED, on_click=lambda _: on_back()),
                        ft.Text(zone.name, size=26, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(f"{ZONE_LABELS[zone.kind]} · {zone.territory}", color=TEXT),
                        ft.Text(EMPTY_POTS if pots == 0 else f"🌱 × {pots}", color=GREEN, size=16),
                    ],
                ),
            ),
        ),
    )


def mount(page: ft.Page, actions: Actions, make_canvas: MakeCanvas) -> None:
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=GREEN)
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    # Календарі (DatePicker) українською.
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("uk", "UA")],
        current_locale=ft.Locale("uk", "UA"),
    )

    current: dict[str, ft.Control | None] = {"screen": None}

    def show(control: ft.Control) -> None:
        current["screen"] = control
        page.controls.clear()
        page.add(control)

    def transition(target: ft.Control, forward: bool) -> None:
        """Наближення: старий екран наїжджає на стіл і тане, новий одночасно виростає з глибини.
        Назад — навпаки. Обидва екрани на час анімації лежать в одному Stack.
        """
        old = current["screen"]
        if old is None:
            show(target)
            return
        curve = ft.AnimationCurve.EASE_IN_OUT
        for control in (old, target):
            control.animate_scale = ft.Animation(ZOOM_MS, curve)
            control.animate_opacity = ft.Animation(ZOOM_MS * 2 // 3, curve)
        old_focus, new_focus = (MENU_FOCUS, TABLE_FOCUS) if forward else (TABLE_FOCUS, MENU_FOCUS)
        target.scale = ft.Scale(0.75 if forward else 1.8, alignment=new_focus)
        target.opacity = 0
        old_layer = fill(ft.Container(content=old))
        stage = ft.Stack(expand=True, controls=[fill(ft.Container(content=target)), old_layer])
        current["screen"] = stage
        page.controls.clear()
        page.add(stage)
        time.sleep(0.05)
        old.scale = ft.Scale(2.0 if forward else 0.7, alignment=old_focus)
        old.opacity = 0
        target.scale = ft.Scale(1.0, alignment=new_focus)
        target.opacity = 1
        page.update()
        time.sleep(ZOOM_MS / 1000)
        stage.controls.remove(old_layer)
        stage.update()

    def not_ready() -> None:
        """Друзі й налаштування поки лише кнопки."""

    def scene_for(zone: Zone) -> Callable[[], ft.Control] | None:
        """Сцена зони для розмитого фону меню: той самий стіл з її горщиками, без «+»."""
        if zone.kind not in SCENE_KINDS:
            return None
        try:
            view = actions.open_zone(zone.id)
        except ZoneNotFound:
            return None

        def build() -> ft.Control:
            canvas = make_canvas(lambda _pot_id: None, lambda _pot_id, _x, _y: None)
            canvas.show(view)
            # Стіл «здалеку»: уся сцена менша і розчиняється в повному фото по краях.
            far = ft.ShaderMask(
                content=ft.Container(
                    content=canvas.control(),
                    scale=ft.Scale(MENU_SCENE_SCALE, alignment=MENU_SCENE_PIVOT),
                ),
                shader=ft.RadialGradient(
                    center=_far_center(),
                    radius=MENU_SCENE_SCALE / 2,  # до краю зменшеної сцени по короткій стороні
                    colors=[ft.Colors.WHITE, ft.Colors.WHITE, ft.Colors.TRANSPARENT],
                    stops=[0.0, 0.6, 1.0],
                ),
                blend_mode=ft.BlendMode.DST_IN,
            )
            return ft.Stack(
                expand=True,
                controls=[
                    fill(ft.Image(src=FARM_BG, fit=ft.BoxFit.COVER)),
                    fill(far),
                ],
            )

        return build

    def home(animated: bool = False) -> ft.Control:
        screen = home_view(
            actions,
            on_open_zone=open_zone,
            on_friends=not_ready,
            on_settings=not_ready,
            on_new_zone=go_new_zone,
            scene_for=scene_for,
        )
        if animated:
            transition(screen, forward=False)
        else:
            show(screen)
        return screen

    def go_home() -> None:
        home()

    def back_home() -> None:
        home(animated=True)

    def go_onboarding() -> None:
        show(onboarding_view(actions, on_done=go_home))

    def go_new_zone() -> None:
        show(onboarding_view(actions, on_done=go_home, ask_nickname=False, on_cancel=go_home))

    def open_zone() -> None:
        zone = _pick_zone(actions)
        if zone is None:
            go_onboarding()
            return
        try:
            view = actions.open_zone(zone.id)
        except ZoneNotFound:
            go_home()
            return
        if zone.kind in SCENE_KINDS:
            select: dict[str, Callable[[str], None]] = {}
            canvas = make_canvas(
                lambda pot_id: select["open"](pot_id) if "open" in select else None,
                lambda _pot_id, _x, _y: None,
            )
            screen = zone_view(
                actions,
                view,
                canvas,
                on_back=back_home,
                on_changed=lambda _v: None,
                bind_select=lambda handler: select.__setitem__("open", handler),
            )
        else:
            screen = _zone_stub(view.zone, len(view.cards), back_home)
        transition(screen, forward=True)

    if actions.list_zones():
        go_home()
    else:
        go_onboarding()

