"""Верстка на фейкових даних. Запуск: flet run app/shell/demo.py

FakeActions уже має теплицю, тож одразу відкривається головне меню.
Екран першого входу видно через main.py (там фейк порожній).
"""

import flet as ft

from app.contracts.fakes import FakeActions
from app.shell import mount


class _TextCanvas:
    """Заглушка карти для демо оболонки. Справжня карта — app.garden."""

    def __init__(self, on_select_pot, on_move_pot) -> None:
        self._text = ft.Text("карта")

    def control(self) -> ft.Control:
        return self._text

    def show(self, view) -> None:
        self._text.value = f"карта: {len(view.cards)} горщики"

    def spawn_point(self) -> tuple[float, float]:
        return 500.0, 500.0


def main(page: ft.Page) -> None:
    mount(page, FakeActions(), _TextCanvas)


if __name__ == "__main__":
    ft.run(main, assets_dir="../../assets")
