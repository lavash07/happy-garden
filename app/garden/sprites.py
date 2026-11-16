"""Який вигляд у горщика. Таблиця — у TASK.md. Тут немає Flet."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.models import Pot, SpeciesProfile


@dataclass(frozen=True)
class SpriteSpec:
    title: str
    glyph: str
    color_hex: str
    scale: float
    fruit_count: int
    face: str
    droop: bool


def sprite_for(species: SpeciesProfile, pot: Pot) -> SpriteSpec:
    raise NotImplementedError("app/garden/sprites.py sprite_for — див. TASK.md")
