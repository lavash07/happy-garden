"""Палітра і фон теплиці. Спільне для всіх екранів оболонки."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

BG = "#F4F7F2"
GREEN = "#2E7D32"
CARD = "#FFFFFF"
TEXT = "#1B2E1B"
DANGER = "#C62828"
WARNING = "#EF6C00"
INFO = "#1565C0"

# Шлях відносно assets/. Оригінал 4096 px лежить у корені, тут легша копія для вебу.
GREENHOUSE_BG = "backgrounds/greenhouse.jpg"

MIN_TAP = 44


def fill(control: ft.Control) -> ft.Control:
    """Розтягнути шар на весь Stack."""
    control.left = 0
    control.top = 0
    control.right = 0
    control.bottom = 0
    return control


def greenhouse_backdrop(
    blur: float = 18,
    clear_center: bool = True,
    veil: float = 0.12,
    make_scene: Callable[[], ft.Control] | None = None,
) -> list[ft.Control]:
    """Шари фону для Stack: розмита сцена, а ближче до центру вона чітка.

    make_scene будує сцену (за замовчуванням фото теплиці). Її кличуть двічі:
    один екземпляр розмивається, другий видно крізь коло.

    1. Сама сцена.
    2. Розмиття всього, що позаду (backdrop blur), і легка біла вуаль.
    3. Та сама картинка ще раз, але з радіальною маскою: у центрі видно повністю,
       до країв плавно зникає в розмиття.
    """
    scene = make_scene or (lambda: ft.Image(src=GREENHOUSE_BG, fit=ft.BoxFit.COVER))
    layers: list[ft.Control] = [
        fill(ft.Container(content=scene())),
        fill(
            ft.Container(
                blur=ft.Blur(blur, blur, ft.BlurTileMode.MIRROR),
                bgcolor=ft.Colors.with_opacity(veil, CARD),
            )
        ),
    ]
    if clear_center:
        layers.append(
            fill(
                ft.ShaderMask(
                    content=scene(),
                    shader=ft.RadialGradient(
                        center=ft.Alignment(0, -0.02),
                        radius=0.5,
                        colors=[
                            ft.Colors.WHITE,
                            ft.Colors.WHITE,
                            ft.Colors.with_opacity(0.4, ft.Colors.WHITE),
                            ft.Colors.TRANSPARENT,
                        ],
                        stops=[0.0, 0.36, 0.68, 1.0],
                    ),
                    blend_mode=ft.BlendMode.DST_IN,
                )
            )
        )
    return layers

