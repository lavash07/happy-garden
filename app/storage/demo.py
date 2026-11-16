"""Запуск: python -m app.storage.demo"""

from app.storage.store import GardenStore


def main() -> None:
    store = GardenStore("happygarden.db")
    print(store.schema)
    try:
        store.get_settings()
    except NotImplementedError as exc:
        print(exc)


if __name__ == "__main__":
    main()
