# Людина 1, частина B — фасад і збірка

Це та сама людина, що писала `app/core`. Починай, коли рушій і тести з `app/core/TASK.md` зелені, а сусідні папки вже мають робочі методи. Поки сусід кидає `NotImplementedError`, `main.py` лишається заглушкою.

Прочитай `docs/ARCHITECTURE.md` і `docs/RULES.md`.

Працюй у `app/wiring/actions.py` і в тілі `main.py`. Контракти не змінюй.

## Що зробити

`GardenActions` реалізує кожен метод протоколу `Actions`. Перевірки назв і координат ідуть через `app.contracts.checks`. Час рослин — `sim_now(settings)`. Час погоди — `real_now()`.

`open_zone` виконує кроки з розділу «Порядок open_zone» в архітектурі. Полив, добриво і збір: створити подію, зберегти її, відкрити зону знову. Горщик уже має бути в базі до події.

`shift_days` додає ціле число до `debug_day_offset`, зберігає налаштування і повертає новий зсув.

`leaderboard` бере `your_score` і друзів із бази. Очки друга — це збережене число, його не перераховуй.

`widgets` повертає картку всієї грядки і по картці на кожну зону.

`describe` і `plant` беруть культуру з каталогу. Невідома назва віддає `SpeciesNotFound`, яке вже кидає каталог.

## Збірка в `main.py`

Коли методи фасаду працюють, заміни заглушку:

```python
store = GardenStore("happygarden.db")
actions = GardenActions(
    store=store,
    catalog=FarmingCatalog(),
    weather=WeatherService(),
    growth=GrowthEngine(),
    care=CarePlanner(),
    groups=GroupBuilder(),
    scores=Scoreboard(),
    reminders=ReminderService(store),
    widgets=WidgetBoard(store),
)
mount(page, actions, GardenMap)
```

Імпорти додай зверху. Правила росту в `main.py` не пиши.

## Сценарій, який має пройтися руками

1. Створити теплицю в Києві.
2. Посадити огірок на суглинку, побачити довідку.
3. Відкрити горщик, полити, побачити зміну настрою.
4. Натиснути «+1 день» кілька разів і побачити іншу стадію.
5. Посадити ще два огірки і зібрати групу.
6. Побачити банер погоди або чесне повідомлення, що мережа недоступна.
7. Відкрити друзів і побачити свої очки.
8. Запустити і `flet run main.py`, і `flet run --web main.py`.

`python -m unittest discover -s tests` перед цим зелений.
