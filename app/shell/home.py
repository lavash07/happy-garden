"""Головне меню: розмита теплиця, у центрі вона чітка. Тап по центру або свайп вгору — у зону.

Над колом по дузі — профілі зон, стрілки по краях гортають, якщо їх більше трьох.
Під колом: «Друзі» зліва, «+» нова зона по центру, «Налаштування» справа.
Зверху назва вибраної зони. Фон — сцена зони (для фазенди стіл з її горщиками), якщо mount її дає;
інакше фото теплиці, а горщики зони стоять у колі.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Callable
from dataclasses import replace

import flet as ft
import flet.canvas as cv

from app.contracts.labels import (
    APP_NAME,
    BTN_CREATE_ZONE,
    BTN_ENTER,
    BTN_FRIENDS,
    BTN_SETTINGS,
    HINT_SWIPE,
    ZONE_LABELS,
)
from app.contracts.models import Zone, ZoneKind, ZoneView
from app.contracts.ports import Actions
from app.contracts.pictures import PICTURE_RATIO, pot_picture
from app.shell.theme import CARD, GREEN, TEXT, fill, greenhouse_backdrop
from app.shell.weather_banner import WeatherBanner, poll_alerts

SWIPE_MIN_PX = 40

# Геометрія сцени. Ширина вміщається в телефон 375 px з полями 16.
CIRCLE = 240
R = CIRCLE / 2
STAGE_W = 340
CY = 190  # центр кола від верху сцени

ARC_R = R + 30  # середня лінія вигнутого меню профілів
BAND_W = 50  # товщина вигнутого меню
CHIP_W, CHIP_H = 104, 36
ARC_SLOTS = 3
ARC_STEP = 40  # градуси між профілями
ARROW = 34
ARROW_ANGLE = 70  # стрілки на -90 ∓ 70, тобто на -160° і -20°
BAND_PAD = 8  # градуси запасу на кінцях меню

ROUND_BTN = 60
ORBIT_R = R + 40
SIDE_ANGLES = (125, 55)  # «Друзі» зліва-знизу, «Налаштування» справа-знизу
PLUS_DROP = 45  # «+» на стільки нижче краю кола
LABEL_H = 22
STAGE_H = CY + R + PLUS_DROP + ROUND_BTN / 2 + 12

ZONE_ICONS: dict[ZoneKind, ft.IconData] = {
    ZoneKind.GREENHOUSE: ft.Icons.ECO_ROUNDED,  # паросток
    ZoneKind.GARDEN: ft.Icons.AGRICULTURE_ROUNDED,  # трактор
    ZoneKind.FARM: ft.Icons.HOUSE_ROUNDED,  # домик
}

# Горщики зони в колі, коли власної сцени в зони немає.
FRUIT_SIZE = 64
MAX_FRUITS = 8

_SHADOW = ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.18, TEXT), offset=ft.Offset(0, 4))


def _polar(radius: float, angle_deg: float) -> tuple[float, float]:
    """Точка навколо центру кола, у координатах сцени. Вісь y вниз."""
    rad = math.radians(angle_deg)
    return STAGE_W / 2 + radius * math.cos(rad), CY + radius * math.sin(rad)


def _place(control: ft.Control, x: float, y: float, w: float, h: float) -> ft.Control:
    """Поставити control центром у точку (x, y)."""
    return ft.Container(left=x - w / 2, top=y - h / 2, width=w, height=h, content=control)


def _current_zone(actions: Actions, zones: list[Zone]) -> Zone | None:
    if not zones:
        return None
    last = actions.get_settings().last_zone_id
    return next((zone for zone in zones if zone.id == last), zones[0])


def _arc_angles(count: int) -> list[float]:
    """Кути для видимих профілів, симетрично від верху кола (-90°)."""
    first = -90 - ARC_STEP * (count - 1) / 2
    return [first + ARC_STEP * i for i in range(count)]


def _arc_shape(
    start_deg: float,
    end_deg: float,
    color: str,
    width: float,
    blur: float | None = None,
    dy: float = 0,
) -> cv.Arc:
    """Товста дуга з круглими кінцями по середній лінії меню."""
    return cv.Arc(
        x=STAGE_W / 2 - ARC_R,
        y=CY - ARC_R + dy,
        width=2 * ARC_R,
        height=2 * ARC_R,
        start_angle=math.radians(start_deg),
        sweep_angle=math.radians(end_deg - start_deg),
        paint=ft.Paint(
            color=color,
            stroke_width=width,
            style=ft.PaintingStyle.STROKE,
            stroke_cap=ft.StrokeCap.ROUND,
            blur_image=blur,
        ),
    )


def _band_span(visible: int, arrows: bool) -> tuple[float, float]:
    if arrows:
        return -90 - ARROW_ANGLE - BAND_PAD, -90 + ARROW_ANGLE + BAND_PAD
    half_chip = math.degrees(CHIP_W / 2 / ARC_R)
    half = ARC_STEP * (visible - 1) / 2 + half_chip + BAND_PAD / 2
    return -90 - half, -90 + half


# Текст по дузі. У Flet немає виміру тексту, тож ширину літер беремо наближено (частки кегля).
FONT = 12.5
ICON = 16
ICON_GAP = 4
CHIP_PAD = 9
_NARROW = set("іїijlI!.,:;'|ʼ ")
_SEMI = set("frtгґ-")
_WIDE = set("шщжмюфыШЩЖМЮФЫmwMW")


def _char_w(ch: str) -> float:
    if ch in _NARROW:
        em = 0.28
    elif ch in _SEMI:
        em = 0.44
    elif ch in _WIDE:
        em = 0.82
    elif ch.isupper():
        em = 0.66
    else:
        em = 0.55
    return em * FONT


def _fit(text: str, max_w: float) -> str:
    """Обрізати назву під довжину дуги, додавши «…»."""
    if sum(_char_w(c) for c in text) <= max_w:
        return text
    room = max_w - _char_w("…")
    out = ""
    for ch in text:
        if sum(_char_w(c) for c in out + ch) > room:
            break
        out += ch
    return out.rstrip() + "…"


def _deg(arc_len: float) -> float:
    """Довжина вздовж дуги меню → градуси."""
    return math.degrees(arc_len / ARC_R)


def _menu(
    span: tuple[float, float],
    slots: list[tuple[Zone, float, bool]],
    on_pick: Callable[[Zone], None],
) -> list[ft.Control]:
    """Вигнуте меню профілів: смуга, рамки, іконки й літери — усе вздовж дуги.

    Повертає canvas (смуга, рамка вибраного, літери), іконки і прозорі зони для натискання.
    """
    shapes: list[cv.Shape] = [
        _arc_shape(*span, ft.Colors.with_opacity(0.16, TEXT), BAND_W, blur=8, dy=4),
        _arc_shape(*span, ft.Colors.with_opacity(0.82, CARD), BAND_W),
    ]
    icons: list[ft.Control] = []
    taps: list[ft.Control] = []
    half = _deg(CHIP_W / 2)
    cap = _deg(CHIP_H / 2)  # круглий кінець штриха додає пів товщини з кожного боку

    for zone, angle, selected in slots:
        if selected:
            shapes.append(_arc_shape(angle - half + cap, angle + half - cap, ft.Colors.with_opacity(0.25, TEXT), CHIP_H, blur=5, dy=2))
            shapes.append(_arc_shape(angle - half + cap, angle + half - cap, GREEN, CHIP_H))
        fg = CARD if selected else TEXT
        text = _fit(zone.name, CHIP_W - 2 * CHIP_PAD - ICON - ICON_GAP)
        widths = [_char_w(c) for c in text]
        pos = -(ICON + ICON_GAP + sum(widths)) / 2  # зсув від центру слота вздовж дуги

        icon_angle = angle + _deg(pos + ICON / 2)
        ix, iy = _polar(ARC_R, icon_angle)
        icons.append(
            _place(
                ft.Icon(
                    ZONE_ICONS[zone.kind],
                    color=CARD if selected else GREEN,
                    size=ICON,
                    rotate=ft.Rotate(math.radians(icon_angle + 90)),
                ),
                ix,
                iy,
                ICON,
                ICON,
            )
        )
        pos += ICON + ICON_GAP

        style = ft.TextStyle(size=FONT, weight=ft.FontWeight.W_600, color=fg)
        for ch, width in zip(text, widths):
            theta = angle + _deg(pos + width / 2)
            x, y = _polar(ARC_R, theta)
            shapes.append(
                cv.Text(
                    x=x,
                    y=y,
                    value=ch,
                    style=style,
                    alignment=ft.Alignment.CENTER,
                    rotate=math.radians(theta + 90),
                )
            )
            pos += width

        tx, ty = _polar(ARC_R, angle)
        taps.append(
            _place(
                ft.Container(
                    width=CHIP_W,
                    height=CHIP_H,
                    border_radius=CHIP_H,
                    on_click=lambda _, z=zone: on_pick(z),
                    tooltip=f"{zone.name} · {ZONE_LABELS[zone.kind]}",
                    rotate=ft.Rotate(math.radians(angle + 90)),
                ),
                tx,
                ty,
                CHIP_W,
                CHIP_H,
            )
        )

    canvas = cv.Canvas(width=STAGE_W, height=STAGE_H, shapes=shapes)
    return [canvas, *icons, *taps]


def _arrow(angle: float, direction: int, on_click: Callable[[ft.Event], None], enabled: bool) -> ft.Control:
    """Стрілка на кінці меню. Дивиться вздовж дуги, туди, куди меню загинається.

    direction=-1 — лівий кінець (кут зменшується), +1 — правий (кут збільшується).
    """
    rad = math.radians(angle)
    dx, dy = -math.sin(rad) * direction, math.cos(rad) * direction  # дотична до кола
    button = ft.Container(
        width=ARROW,
        height=ARROW,
        border_radius=ARROW,
        bgcolor=ft.Colors.with_opacity(0.14, GREEN) if enabled else ft.Colors.TRANSPARENT,
        ink=enabled,
        on_click=on_click if enabled else None,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(
            ft.Icons.ARROW_FORWARD_ROUNDED,
            color=GREEN if enabled else ft.Colors.with_opacity(0.3, TEXT),
            size=20,
            rotate=ft.Rotate(math.atan2(dy, dx)),
        ),
    )
    x, y = _polar(ARC_R, angle)
    return _place(button, x, y, ARROW, ARROW)


def _round_button(
    icon: ft.IconData,
    on_click: Callable[[ft.Event], None],
    tooltip: str,
    label: str | None = None,
) -> ft.Control:
    circle = ft.Container(
        width=ROUND_BTN,
        height=ROUND_BTN,
        border_radius=ROUND_BTN,
        bgcolor=ft.Colors.with_opacity(0.9, CARD),
        shadow=_SHADOW,
        ink=True,
        on_click=on_click,
        tooltip=tooltip,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(icon, color=GREEN, size=28),
    )
    if label is None:
        return circle
    return ft.Column(
        tight=True,
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            circle,
            ft.Container(
                height=LABEL_H,
                padding=ft.Padding(8, 0, 8, 0),
                border_radius=LABEL_H,
                bgcolor=ft.Colors.with_opacity(0.7, CARD),
                content=ft.Row(
                    tight=True,
                    controls=[ft.Text(label, color=TEXT, size=12, weight=ft.FontWeight.W_600)],
                ),
            ),
        ],
    )


def _fruit_controls(actions: Actions, zone: Zone | None) -> list[ft.Control]:
    """Горщики вибраної зони для кола. Картинки — з app.contracts.pictures, без них glyph."""
    if zone is None:
        return []
    try:
        view: ZoneView = actions.open_zone(zone.id)
    except Exception:  # noqa: BLE001 — фон меню не має падати через зону
        return []
    images: list[ft.Control] = []
    for card in view.cards[:MAX_FRUITS]:
        src = pot_picture(card.pot.profile.species_id, card.pot.stage)
        if src:
            images.append(ft.Image(src=src, width=FRUIT_SIZE * PICTURE_RATIO, height=FRUIT_SIZE, fit=ft.BoxFit.CONTAIN))
        else:
            images.append(ft.Text(card.species.glyph, size=FRUIT_SIZE * 0.5))
    return images


def home_view(
    actions: Actions,
    on_open_zone: Callable[[], None],
    on_friends: Callable[[], None],
    on_settings: Callable[[], None],
    on_status: Callable[[], None] | None = None,
    on_new_zone: Callable[[], None] | None = None,
    scene_for: Callable[[Zone], Callable[[], ft.Control] | None] | None = None,
) -> ft.Control:
    """on_status поки не має кнопки: картки стану додасть людина 2."""
    del on_status

    title = ft.Text("", size=24, weight=ft.FontWeight.BOLD, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    caption = ft.Text("", size=13, color=ft.Colors.with_opacity(0.75, TEXT))
    # Смуга меню (canvas) лежить під колом, бо canvas забирає натискання; кнопки — над ним.
    band = ft.Stack(width=STAGE_W, height=STAGE_H)
    arc = ft.Stack(width=STAGE_W, height=STAGE_H)
    backdrop = ft.Stack(expand=True)
    fruits = ft.Row(
        wrap=True,
        spacing=4,
        run_spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )
    state = {"offset": 0, "weather_for": None}
    banner = WeatherBanner()

    def start_weather(zone: Zone | None) -> None:
        """Погода зони приходить через фасад у фоні; банер чекає, поки вона з'явиться."""
        state["weather_for"] = zone.id if zone else None
        banner.loading()
        if zone is None:
            return
        threading.Thread(
            target=poll_alerts,
            args=(
                lambda: actions.open_zone(zone.id).alerts,
                banner,
                lambda: state["weather_for"] == zone.id,
            ),
            daemon=True,
        ).start()

    def refresh() -> None:
        zones = actions.list_zones()
        current = _current_zone(actions, zones)
        title.value = current.name if current else APP_NAME
        caption.value = f"{ZONE_LABELS[current.kind]} · {current.territory}" if current else ""
        if current is None or state["weather_for"] != current.id:
            start_weather(current)
        make_scene = scene_for(current) if scene_for and current else None
        backdrop.controls = greenhouse_backdrop(make_scene=make_scene)
        fruits.controls = [] if make_scene else _fruit_controls(actions, current)

        visible = min(ARC_SLOTS, len(zones))
        max_offset = max(0, len(zones) - visible)
        state["offset"] = min(max(state["offset"], 0), max_offset)
        window = zones[state["offset"] : state["offset"] + visible]

        arrows = len(zones) > ARC_SLOTS
        controls: list[ft.Control] = []
        if visible:
            slots = [
                (zone, angle, current is not None and zone.id == current.id)
                for zone, angle in zip(window, _arc_angles(visible))
            ]
            canvas, *menu_controls = _menu(_band_span(visible, arrows), slots, select)
            band.controls = [canvas]
            controls.extend(menu_controls)
        else:
            band.controls = []
        if arrows:
            controls.append(_arrow(-90 - ARROW_ANGLE, -1, lambda _: scroll(-1), state["offset"] > 0))
            controls.append(_arrow(-90 + ARROW_ANGLE, 1, lambda _: scroll(1), state["offset"] < max_offset))
        arc.controls = controls

    def redraw() -> None:
        refresh()
        for control in (title, caption, banner.control(), band, arc, fruits, backdrop):
            control.update()

    def select(zone: Zone) -> None:
        settings = actions.get_settings()
        if settings.last_zone_id != zone.id:
            actions.save_settings(replace(settings, last_zone_id=zone.id))
        redraw()

    def scroll(step: int) -> None:
        state["offset"] += step
        redraw()

    # Почати так, щоб вибрана зона була посередині дуги, якщо можна.
    zones_now = actions.list_zones()
    selected_now = _current_zone(actions, zones_now)
    if selected_now is not None:
        index = next(i for i, zone in enumerate(zones_now) if zone.id == selected_now.id)
        state["offset"] = index - ARC_SLOTS // 2
    refresh()

    drag = {"start": 0.0, "last": 0.0}

    def drag_start(e: ft.DragStartEvent) -> None:
        drag["start"] = drag["last"] = e.global_position.y

    def drag_update(e: ft.DragUpdateEvent) -> None:
        drag["last"] = e.global_position.y

    def drag_end(_: ft.DragEndEvent) -> None:
        if drag["start"] - drag["last"] > SWIPE_MIN_PX:
            on_open_zone()

    fruit_layer = ft.Container(
        width=CIRCLE,
        height=CIRCLE,
        border_radius=CIRCLE,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        padding=ft.Padding(24, 24, 24, 64),
        alignment=ft.Alignment.BOTTOM_CENTER,
        content=fruits,
    )

    # Прозоре коло: через нього видно теплицю і плоди. Тап — у зону.
    portal = ft.GestureDetector(
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=lambda _: on_open_zone(),
        content=ft.Container(
            width=CIRCLE,
            height=CIRCLE,
            border_radius=CIRCLE,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.6, CARD)),
            alignment=ft.Alignment(0, 0.72),
            content=ft.Container(
                padding=ft.Padding(16, 9, 16, 9),
                border_radius=24,
                bgcolor=ft.Colors.with_opacity(0.88, CARD),
                content=ft.Row(
                    tight=True,
                    spacing=6,
                    controls=[
                        ft.Icon(ft.Icons.TOUCH_APP_ROUNDED, color=GREEN, size=20),
                        ft.Text(BTN_ENTER, color=TEXT, weight=ft.FontWeight.W_600),
                    ],
                ),
            ),
        ),
    )

    side_w = 110  # кнопка з підписом
    side_h = ROUND_BTN + 4 + LABEL_H
    bottom: list[ft.Control] = []
    for angle, (label, icon, handler) in zip(
        SIDE_ANGLES,
        (
            (BTN_FRIENDS, ft.Icons.PEOPLE_ALT_ROUNDED, on_friends),
            (BTN_SETTINGS, ft.Icons.SETTINGS_ROUNDED, on_settings),
        ),
    ):
        x, y = _polar(ORBIT_R, angle)
        button = _round_button(icon, lambda _, h=handler: h(), label, label)
        bottom.append(ft.Container(left=x - side_w / 2, top=y - ROUND_BTN / 2, width=side_w, height=side_h, content=button))
    if on_new_zone is not None:
        plus = _round_button(ft.Icons.ADD_ROUNDED, lambda _: on_new_zone(), BTN_CREATE_ZONE)
        bottom.append(_place(plus, STAGE_W / 2, CY + R + PLUS_DROP, ROUND_BTN, ROUND_BTN))

    circle_left, circle_top = STAGE_W / 2 - R, CY - R
    stage = ft.Stack(
        width=STAGE_W,
        height=STAGE_H,
        controls=[
            fill(band),
            ft.Container(left=circle_left, top=circle_top, content=fruit_layer),
            ft.Container(left=circle_left, top=circle_top, content=portal),
            fill(arc),
            *bottom,
        ],
    )

    header = ft.Container(
        padding=ft.Padding(20, 8, 20, 8),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.7, CARD),
        content=ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[title, caption, ft.Container(margin=ft.Margin(0, 6, 0, 0), content=banner.control())],
        ),
    )

    hint = ft.Container(
        padding=ft.Padding(16, 4, 16, 8),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.7, CARD),
        content=ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.KEYBOARD_ARROW_UP_ROUNDED, color=GREEN, size=26),
                ft.Text(HINT_SWIPE, color=TEXT, size=13, weight=ft.FontWeight.W_500),
            ],
        ),
    )

    overlay = ft.SafeArea(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                expand=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    header,
                    ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=stage),
                    hint,
                ],
            ),
        )
    )

    return ft.GestureDetector(
        expand=True,
        on_vertical_drag_start=drag_start,
        on_vertical_drag_update=drag_update,
        on_vertical_drag_end=drag_end,
        animate_scale=ft.Animation(420, ft.AnimationCurve.EASE_IN),
        animate_opacity=ft.Animation(420, ft.AnimationCurve.EASE_IN),
        content=ft.Stack(expand=True, controls=[fill(backdrop), fill(overlay)]),
    )
