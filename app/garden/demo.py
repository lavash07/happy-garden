"""Запуск полиці: flet run --web app/garden/demo.py"""

import flet as ft

from app.garden.bench import main

if __name__ == "__main__":
    ft.run(main)
