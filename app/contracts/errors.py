"""Помилки, які інтерфейс ловить і показує текстом. Не вигадуй інші класи."""


class SpeciesNotFound(LookupError):
    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(f"Культуру не знайдено: {query}")


class ZoneNotFound(LookupError):
    def __init__(self, zone_id: str) -> None:
        self.zone_id = zone_id
        super().__init__(f"Зону не знайдено: {zone_id}")


class PotNotFound(LookupError):
    def __init__(self, pot_id: str) -> None:
        self.pot_id = pot_id
        super().__init__(f"Горщик не знайдено: {pot_id}")
