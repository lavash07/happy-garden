"""Запуск: python -m app.knowledge.demo"""

from app.knowledge.catalog import FarmingCatalog
from app.knowledge.weather import WeatherService


def main() -> None:
    catalog = FarmingCatalog()
    weather = WeatherService()
    print(catalog.path)
    try:
        catalog.find("cucumber")
    except NotImplementedError as exc:
        print(exc)
    try:
        weather.alerts("Київ", None, None)  # type: ignore[arg-type]
    except NotImplementedError as exc:
        print(exc)


if __name__ == "__main__":
    main()
