"""Читає app/knowledge/data/species.json у SpeciesProfile. Див. TASK.md."""

from __future__ import annotations

from pathlib import Path

from app.contracts.models import SpeciesProfile


class FarmingCatalog:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or str(Path(__file__).with_name("data") / "species.json")

    def search(self, query: str) -> list[SpeciesProfile]:
        raise NotImplementedError("app/knowledge/catalog.py search — див. TASK.md")

    def find(self, name_or_id: str, variety: str | None = None) -> SpeciesProfile:
        raise NotImplementedError("app/knowledge/catalog.py find — див. TASK.md")
