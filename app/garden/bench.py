"""Полиця з 3D-горщиками. На сайті в ряд, у вузькому вікні стовпчиком."""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

# Координата реального дна всередині прозорого PNG горщика.
POT_FOOT = 0.84
BG_RATIO = 5500 / 3072
PNG_RATIO = 520 / 680
TABLE_RATIO = 1600 / 560

CROPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "cucumber": ("Огірок", ("models/cute_cucumber_pot_ready.png",)),
    "tomato": (
        "Помідор",
        ("models/tomato_stage1.png", "models/tomato_stage2.png", "models/tomato_stage3.png"),
    ),
    "pepper": (
        "Перець",
        (
            "models/cute_pepper_stage1.png",
            "models/cute_pepper_stage2.png",
            "models/cute_pepper_stage3.png",
        ),
    ),
    "potato": (
        "Картопля",
        ("models/potato_stage1.png", "models/potato_stage2.png", "models/potato_stage3.png"),
    ),
    "carrot": (
        "Морква",
        (
            "models/carrot_1.png",
            "models/carrot_2.png",
            "models/carrot_3.png",
            "models/carrot_4.png",
        ),
    ),
}

_STAGE_NAMES = {
    1: ("Готовий горщик",),
    3: ("Паростки", "Кущ", "Плоди"),
    4: ("Посадка", "Паростки", "Ріст", "Стигла"),
}


@dataclass
class ShelfPot:
    id: int
    crop: str
    stage: int
    watered: bool = False


def _stage_name(crop: str, stage: int) -> str:
    count = len(CROPS[crop][1])
    names = _STAGE_NAMES.get(count, ("Паростки", "Ріст", "Плоди", "Стигла"))
    return names[min(stage, len(names) - 1)]


def _picture(crop: str, stage: int) -> str:
    files = CROPS[crop][1]
    return files[min(stage, len(files) - 1)]


def main(page: ft.Page) -> None:
    page.title = "HappyGarden"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#C9D7B5"
    page.theme_mode = ft.ThemeMode.LIGHT

    pots = [
        ShelfPot(1, "pepper", 1),
        ShelfPot(2, "carrot", 1),
        ShelfPot(3, "tomato", 0),
        ShelfPot(4, "tomato", 2),
        ShelfPot(5, "potato", 0),
        ShelfPot(6, "pepper", 2),
        ShelfPot(7, "carrot", 3),
    ]
    state = {
        "pots": pots,
        "next_id": 8,
        "selected": None,
        "crop": "tomato",
        "layout": "auto",
        "status": "Натисни горщик, потім «Полити» — він перейде на наступний вигляд.",
        "drawing": False,
    }

    def phone_layout() -> bool:
        if state["layout"] == "phone":
            return True
        if state["layout"] == "site":
            return False
        return float(page.width or 1200) < 860

    def draw() -> None:
        if state["drawing"]:
            return
        state["drawing"] = True
        page.controls = [_view()]
        page.update()
        state["drawing"] = False

    def select(pot_id: int) -> None:
        state["selected"] = pot_id
        pot = _selected()
        if pot:
            state["status"] = f"{CROPS[pot.crop][0]} · {_stage_name(pot.crop, pot.stage)}"
        draw()

    def choose_crop(crop: str) -> None:
        state["crop"] = crop
        draw()

    def set_layout(mode: str) -> None:
        state["layout"] = mode
        draw()

    def plant(_event=None) -> None:
        crop = state["crop"]
        pot = ShelfPot(state["next_id"], crop, 0)
        state["next_id"] += 1
        state["pots"].append(pot)
        state["selected"] = pot.id
        state["status"] = f"Посаджено: {CROPS[crop][0]} · {_stage_name(crop, 0)}"
        draw()

    def water(_event=None) -> None:
        pot = _selected()
        if pot is None:
            state["status"] = "Спочатку натисни на горщик."
            draw()
            return
        last = len(CROPS[pot.crop][1]) - 1
        pot.watered = True
        if pot.stage < last:
            pot.stage += 1
            state["status"] = f"Полито. {CROPS[pot.crop][0]} тепер: {_stage_name(pot.crop, pot.stage)}"
        else:
            state["status"] = f"Полито. {CROPS[pot.crop][0]} уже на останньому вигляді."
        draw()

    def show_info(_event=None) -> None:
        pot = _selected()
        if pot is None:
            state["status"] = "Оберіть горщик, щоб подивитися інформацію."
        else:
            water_state = "полита" if pot.watered else "очікує поливу"
            state["status"] = (
                f"{CROPS[pot.crop][0]} · {_stage_name(pot.crop, pot.stage)} · {water_state}"
            )
        draw()

    def harvest(_event=None) -> None:
        pot = _selected()
        if pot is None:
            state["status"] = "Спочатку оберіть горщик."
        elif pot.stage < len(CROPS[pot.crop][1]) - 1:
            state["status"] = f"{CROPS[pot.crop][0]} ще не готовий до збору."
        else:
            state["status"] = f"Зібрано врожай: {CROPS[pot.crop][0]}."
            pot.stage = 0
            pot.watered = False
        draw()

    def _selected() -> ShelfPot | None:
        for pot in state["pots"]:
            if pot.id == state["selected"]:
                return pot
        return None

    def _pot_image(pot: ShelfPot, width: float, height: float) -> ft.Control:
        selected = pot.id == state["selected"]
        image = ft.Image(src=_picture(pot.crop, pot.stage), fit=ft.BoxFit.CONTAIN, width=width, height=height)
        badge = ft.Text("💧", size=22) if pot.watered else ft.Container(width=0, height=0)
        label = (
            ft.Container(
                bgcolor="#2E7D32",
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                content=ft.Text(CROPS[pot.crop][0], color="#FFFFFF", size=12),
            )
            if selected
            else ft.Container(width=0, height=0)
        )
        return ft.Container(
            width=width,
            height=height,
            on_click=lambda _event, pot_id=pot.id: select(pot_id),
            content=ft.Stack(
                width=width,
                height=height,
                controls=[
                    image,
                    ft.Container(right=4, top=4, content=badge),
                    ft.Container(bottom=6, left=0, right=0, alignment=ft.Alignment.CENTER, content=label),
                ],
            ),
        )

    def _garden_header(compact: bool = False) -> ft.Control:
        pot = _selected()
        detail = (
            f"{CROPS[pot.crop][0]} · {_stage_name(pot.crop, pot.stage)}"
            if pot
            else "Оберіть або посадіть рослину"
        )
        return ft.Container(
            width=230 if compact else 270,
            bgcolor="#FAF4E4",
            border=ft.Border.all(1, "#D8C8A5"),
            border_radius=18,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Column(
                spacing=1,
                controls=[
                    ft.Text("🌿 HappyGarden", size=20, weight=ft.FontWeight.W_600, color="#214C2A"),
                    ft.Text("Моя теплиця", size=12, color="#6B765F"),
                    ft.Text(detail, size=13, weight=ft.FontWeight.W_600, color="#2E7D32"),
                ],
            ),
        )

    def _action_menu(compact: bool = False) -> ft.Control:
        return ft.Container(
            bgcolor="#FAF4E4",
            border=ft.Border.all(2, "#2E7D32"),
            border_radius=18,
            padding=8,
            content=ft.Row(
                spacing=6,
                wrap=compact,
                controls=[
                    ft.Button(
                        content="💧 Полити",
                        height=38,
                        bgcolor="#1976D2",
                        color="#FFFFFF",
                        on_click=water,
                    ),
                    ft.Button(
                        content="ℹ️ Інфо",
                        height=38,
                        bgcolor="#FFFFFF",
                        color="#214C2A",
                        on_click=show_info,
                    ),
                    ft.Button(
                        content="🧺 Зібрати",
                        height=38,
                        bgcolor="#E88A2D",
                        color="#FFFFFF",
                        on_click=harvest,
                    ),
                ],
            ),
        )

    def _plant_panel(compact: bool = False) -> ft.Control:
        crops = [
            _chip(CROPS[key][0], state["crop"] == key, lambda _event, crop=key: choose_crop(crop))
            for key in CROPS
        ]
        return ft.Container(
            width=260 if compact else 500,
            bgcolor="#FAF4E4",
            border=ft.Border.all(1, "#D8C8A5"),
            border_radius=18,
            padding=10,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.Text("Нова рослина", size=14, weight=ft.FontWeight.W_600, color="#214C2A"),
                            ft.Button(
                                content="🌱 Посадити",
                                height=38,
                                bgcolor="#2E7D32",
                                color="#FFFFFF",
                                on_click=plant,
                            ),
                        ],
                    ),
                    ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6, controls=crops),
                    ft.Text(state["status"], size=12, color="#596751"),
                ],
            ),
        )

    def _site(width: float, height: float) -> ft.Control:
        frame_h = max(height, 280)
        if width / frame_h > BG_RATIO:
            img_w = width
            img_h = width / BG_RATIO
        else:
            img_h = frame_h
            img_w = frame_h * BG_RATIO
        origin_x = (width - img_w) / 2
        origin_y = (frame_h - img_h) / 2
        count = max(len(state["pots"]), 1)
        table_w = img_w * 0.84
        table_h = table_w / TABLE_RATIO
        table_left = origin_x + (img_w - table_w) / 2
        # Альфа-модель має невеликий прозорий відступ знизу; 1.01 ставить
        # фактичні ніжки та підлогову тінь точно на нижню площину доріжки.
        table_top = origin_y + img_h * 1.01 - table_h
        pot_h = min(table_h * 0.48, table_w * 0.12 / PNG_RATIO)
        pot_w = pot_h * PNG_RATIO
        band = table_w * 0.76
        if pot_w * count > band:
            pot_w = band / count
            pot_h = pot_w / PNG_RATIO
        margin = table_left + table_w * 0.12
        span = max(table_w * 0.76, pot_w)
        step = 0 if count == 1 else (span - pot_w) / (count - 1)
        controls: list[ft.Control] = [
            ft.Image(
                src="bg_greenhouse.jpg",
                left=origin_x,
                top=origin_y,
                width=img_w,
                height=img_h,
                fit=ft.BoxFit.FILL,
            ),
            ft.Image(
                src="models/greenhouse_table.png",
                left=table_left,
                top=table_top,
                width=table_w,
                height=table_h,
                fit=ft.BoxFit.FILL,
            ),
        ]
        placements = []
        center = (count - 1) / 2
        for index, pot in enumerate(state["pots"]):
            distance = abs(index - center) / max(center, 1)
            proximity = 1 - distance**2
            scale = 0.94 + 0.08 * proximity
            if pot.id == state["selected"]:
                scale *= 1.14
            draw_w = pot_w * scale
            draw_h = pot_h * scale
            left = margin + index * step - (draw_w - pot_w) / 2
            x_fraction = (left + draw_w / 2 - table_left) / table_w
            surface = 0.36 + 0.055 * x_fraction
            feet = table_top + table_h * (surface + 0.025 * proximity)
            top = feet - draw_h * POT_FOOT
            placements.append((pot, left, top, feet, draw_w, draw_h))

        # Контактні тіні та невелика перспектива прив'язують горщики до стільниці.
        for _pot, left, _top, feet, draw_w, draw_h in placements:
            shadow_w = draw_w * 0.56
            shadow_h = max(draw_h * 0.055, 4)
            controls.append(
                ft.Container(
                    left=left + (draw_w - shadow_w) / 2,
                    top=feet - shadow_h / 2,
                    width=shadow_w,
                    height=shadow_h,
                    bgcolor="#000000",
                    opacity=0.18,
                    border_radius=100,
                )
            )
        for pot, left, top, _feet, draw_w, draw_h in placements:
            controls.append(ft.Container(left=left, top=top, content=_pot_image(pot, draw_w, draw_h)))
        selected_placement = next(
            (placement for placement in placements if placement[0].id == state["selected"]),
            None,
        )
        if selected_placement:
            _pot, left, top, _feet, draw_w, _draw_h = selected_placement
            menu_w = 378
            menu_left = min(max(left + draw_w / 2 - menu_w / 2, 12), width - menu_w - 12)
            controls.append(
                ft.Container(
                    left=menu_left,
                    top=max(top - 58, 92),
                    width=menu_w,
                    content=_action_menu(),
                )
            )
        controls.append(ft.Container(left=16, top=16, content=_garden_header()))
        controls.append(ft.Container(right=16, top=16, content=_plant_panel()))
        return ft.Stack(width=width, height=height, controls=controls)

    def _phone(width: float, height: float) -> ft.Control:
        body = max(height, 240)
        card_w = min(width * 0.42, 180)
        card_h = card_w / PNG_RATIO
        cards = [
            ft.Container(margin=ft.Margin.only(top=12), content=_garden_header(compact=True)),
            _plant_panel(compact=True),
        ]
        for pot in state["pots"]:
            selected = pot.id == state["selected"]
            card_controls = [
                _pot_image(pot, card_w, card_h),
                ft.Container(
                    bgcolor="#F6EBD2",
                    border_radius=10,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    content=ft.Text(
                        f"{CROPS[pot.crop][0]} · {_stage_name(pot.crop, pot.stage)}",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color="#1B2E1B",
                    ),
                ),
            ]
            if selected:
                card_controls.append(_action_menu(compact=True))
            cards.append(
                ft.Container(
                    margin=ft.Margin.only(top=4),
                    width=card_w + 28,
                    bgcolor="#FAF4E4",
                    padding=8,
                    border=ft.Border.all(3 if selected else 1, "#2E7D32" if selected else "#D8C8A5"),
                    border_radius=20,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                        controls=card_controls,
                    ),
                )
            )
        if not state["pots"]:
            cards.append(ft.Text("Полиця порожня. Посади першу рослину.", color="#1B2E1B", size=16))
        return ft.Stack(
            width=width,
            height=body,
            controls=[
                ft.Image(src="bg_greenhouse.jpg", width=width, height=body, fit=ft.BoxFit.COVER),
                ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    width=width,
                    height=body,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=cards,
                ),
            ],
        )

    def _chip(text: str, active: bool, click) -> ft.Control:
        return ft.Button(
            content=text,
            height=38,
            bgcolor="#2E7D32" if active else "#FFFFFF",
            color="#FFFFFF" if active else "#1B2E1B",
            on_click=click,
        )

    def _view() -> ft.Control:
        width = float(page.width or 1200)
        height = float(page.height or 800)
        if phone_layout():
            return _phone(width, height)
        return _site(width, height)

    page.on_resize = lambda _event: draw()
    draw()
