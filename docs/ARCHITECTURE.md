# Як частини з'єднуються

Усі клонують **весь** репозиторій. Окрема папка без решти не запускається: імпорти йдуть через `app.contracts`.

Людина працює лише у своїй папці. `app/contracts` уже готовий. Його змінює тільки людина ядра, і лише якщо разом із цим змінюється `docs/RULES.md`. Інші, якщо бракує поля, пишуть це в `NOTES.md` у своїй папці і не вигадують паралельну модель.

## Хто за що

| Людина | Модель | Папки |
| --- | --- | --- |
| 1 | Opus | `app/core`, `app/wiring`, збірка `main.py` |
| 2 | безкоштовна | `app/shell` |
| 3 | безкоштовна | `app/garden` |
| 4 | безкоштовна | `app/knowledge` |
| 5 | безкоштовна | `app/storage` |

## Кому що можна імпортувати

| Папка | Імпортує |
| --- | --- |
| `app/contracts` | лише стандартну бібліотеку |
| `app/core` | `app.contracts` і сусідні файли в `app/core` |
| `app/knowledge` | `app.contracts`, `httpx` |
| `app/storage` | `app.contracts`, `sqlite3` |
| `app/garden` | `app.contracts`, `flet`, свої файли |
| `app/shell` | `app.contracts`, `flet`, свої файли |
| `app/wiring` | `app.contracts`, `app.core`, `app.knowledge`, `app.storage` |
| `main.py` | `flet`, `app.wiring`, `app.shell`, `app.garden` |

`app/shell` не імпортує карту. `main.py` передає клас `GardenMap` у `mount`. У демо оболонка користується `FakeActions` з `app.contracts.fakes`.

## Єдиний вхід для екранів

Екрани викликають методи `Actions` з `app.contracts.ports`. Вони отримують готові `ZoneView`, `PotCard`, `WidgetSnapshot`, `LeaderboardRow`. Відсотки показують через `as_percent`. Усі написи беруть з `app.contracts.labels`.

Зміни контракту від 16.11 (людина 1, сумісні, старі виклики працюють):

- `Actions.plant(..., planted_at=None)` — посадка в минулому. Фасад додає припущені поливи (`docs/RULES.md`, «Посадка в минулому»).
- `Actions.water(..., at=None)` і `fertilize(..., at=None)` — догляд, записаний пізніше.
- `PotCard.forecast: GrowthForecast | None` — коли наступний етап і стиглість. Рахує `app/core/forecast.py`, фасад кладе в картку на кроці 8 `open_zone`.
- Сорти: у `species.json` кілька записів з тим самим `species_id` і різним `variety`. `find(name, variety)` повертає запис сорту, і прогноз іде за його днями етапів.

`FakeActions` малює вітрину для верстки. Це не правила росту. Правила лише в `docs/RULES.md`.

Перевірки назв, ніків, ґрунту і меж карти: `app.contracts.checks`. І фейк, і справжній фасад викликають їх.

## Порядок `open_zone`

Це єдина послідовність перерахунку. Вона живе в `app/wiring/actions.py`.

1. Прочитати налаштування. `sim = sim_now(settings)`, `real = real_now()`.
2. Взяти зону, горщики, групи, події зони.
3. Для кожного горщика знайти довідку через `catalog.find(species_id, variety)`.
4. `growth.advance(pot, species, events_of_this_pot, sim)` і зберегти горщик.
5. `care.plan(...)` на вже перерахований горщик.
6. `weather.alerts(zone.territory, species, real)` для кожної культури зони. У `ZoneView` лишай унікальні попередження за парою рівня і заголовка, щоб три огірки не дали три однакові банери.
7. `reminders.sync(plans, alerts, sim, zone_id, notify_water, notify_weather)`.
8. Зібрати `ZoneView` через картки `PotCard`: горщик, довідка, план, `growth.timeline(profile, species)`.

Полив, добриво і збір роблять одне й те саме: `growth.make_event`, `store.add_event`, потім `open_zone`. Горщик зберігають до події, бо база бере `zone_id` з уже записаного горщика.

`advance` чиста функція: ті самі дата, довідка і журнал дають ті самі показники. Координати і `group_id` вона залишає як у переданому горщику.

## Карта

Оболонка створює полотно так:

```python
canvas = make_canvas(on_select_pot, on_move_pot)
page.add(canvas.control())
canvas.show(view)
x, y = canvas.spawn_point()
```

`on_select_pot(pot_id)` відкриває картку. `on_move_pot(pot_id, world_x, world_y)` викликає `actions.move_pot` і знову `show`.

Перетворення координат належить тільки карті:

```text
screen_x = (world_x - center_x) * zoom + width / 2
screen_y = (world_y - center_y) * zoom + height / 2
world_x = (screen_x - width / 2) / zoom + center_x
world_y = (screen_y - height / 2) / zoom + center_y
```

Перший `show` ставить камеру на середню точку горщиків. Наступні `show` камеру не чіпають, інакше кожен полив стрибатиме карту в центр.

Рамка групи малюється навколо її горщиків. Поле `x, y` групи — запасний центр, для рамки беруться живі координати горщиків.

## База

Один JSON-об'єкт у колонці `data`, зібраний функціями з `app.contracts.codec`. Окремі колонки лише для id і пошуку. Таблиця груп називається `groups_`, бо `GROUP` у SQL зайняте.

Нова база без рядка налаштувань повертає `Settings()`.

## Перевірка стику

`python -m unittest discover -s tests` має лишатися зеленим. Тест порівнює методи фасаду, рушія, довідки і бази з протоколами. Перейменування методу ламає тест навмисно.
