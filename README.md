# HappyGarden

Віртуальна теплиця, город і фазенда. Один код на Python відкривається як сайт і збирається як застосунок на iPhone. Команда не пише JavaScript.

Ідея і межі хакатону — у [CONCEPT.md](CONCEPT.md). Як папки стикуються — у [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Формули росту — у [docs/RULES.md](docs/RULES.md).

## Що вже лежить у репозиторії

Готовий спільний шар `app/contracts`: моделі, написи українською, перевірки форм, календар етапів, розбір JSON і `FakeActions` для верстки екранів.

У `app/core`, `app/shell`, `app/garden`, `app/knowledge`, `app/storage` і `app/wiring` стоять функції з потрібними аргументами. Тіла ще кидають `NotImplementedError`. Біля кожної папки є `TASK.md` — це завдання для людини і для моделі, яка писатиме код.

`main.py` поки показує каркас. Його замінює людина 1, коли решта методів уже працює.

## Як запустити

Потрібен Python 3.11 або новіший.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
flet run main.py
flet run --web main.py
```

Окремі чернетки екранів: `flet run app/shell/demo.py` і `flet run app/garden/demo.py`.

iPhone збирається тим самим `main.py` на Mac із Xcode: `flet build ios`. Для захисту хакатону достатньо вікна і браузера, якщо збірку на телефон не встигнете.

## Хто що робить

Кожен клонує весь репозиторій і пише лише у своїй папці. Одну папку окремо копіювати не варто: імпорти тримаються на спільному контракті.

| Людина | Модель | Папка | Завдання |
| --- | --- | --- | --- |
| 1 | Opus | `app/core`, потім `app/wiring` і `main.py` | Ріст, полив, групи, очки і збірка всього разом |
| 2 | безкоштовна | `app/shell` | Меню, свайп, форми, друзі, налаштування |
| 3 | безкоштовна | `app/garden` | Карта: пан, зум, горщики, личка, групи |
| 4 | безкоштовна | `app/knowledge` | Довідка культур і погода Open-Meteo |
| 5 | безкоштовна | `app/storage` | База, нагадування, картки стану |

Людина з Opus тримає правила і стики: там багато крайових випадків, і від цього залежить решта. Інші малюють екрани і підключають зовнішні речі за вже заданими методами. `app/contracts` вони не редагують. Якщо не вистачає поля, пишуть `NOTES.md` у своїй папці.

Поки рушій не готовий, екрани верстаються на `FakeActions`: там уже є теплиця, три огірки групою, спраглий горщик і сумний помідор.

## Текст для моделі кожної людини

Вставте його в чат разом із репозиторієм. Модель має читати `TASK.md`, а не вигадувати власну структуру.

Людина 1:

```text
Ти людина 1 у проєкті HappyGarden. Прочитай README.md, CONCEPT.md, docs/ARCHITECTURE.md, docs/RULES.md, app/core/TASK.md. Реалізуй app/core і тести. app/contracts не змінюй. Чужі папки не змінюй. app/contracts/fakes.py не використовуй як специфікацію росту. Коли рушій і тести зелені, прочитай app/wiring/TASK.md і збери фасад та main.py.
```

Людина 2:

```text
Ти людина 2 у проєкті HappyGarden. Прочитай CONCEPT.md, docs/ARCHITECTURE.md і app/shell/TASK.md. Реалізуй лише app/shell. Бери дані з Actions. Для демо використовуй FakeActions. Написи бери з app.contracts.labels. app.garden, app.core, app.knowledge, app.storage і app.contracts не змінюй.
```

Людина 3:

```text
Ти людина 3 у проєкті HappyGarden. Прочитай CONCEPT.md, розділ «Карта» в docs/ARCHITECTURE.md і app/garden/TASK.md. Реалізуй лише app/garden: GardenMap і sprite_for. Стан рослин не перераховуй. app.shell і app.contracts не змінюй.
```

Людина 4:

```text
Ти людина 4 у проєкті HappyGarden. Прочитай CONCEPT.md, docs/ARCHITECTURE.md і app/knowledge/TASK.md. Реалізуй лише app/knowledge і доповни species.json трьома культурами з реальними джерелами. Формули росту не пиши. Дощ не змінює вологу горщика.
```

Людина 5:

```text
Ти людина 5 у проєкті HappyGarden. Прочитай docs/ARCHITECTURE.md і app/storage/TASK.md. Реалізуй лише app/storage: SQLite через codec, нагадування і картки стану. Нових формул здоров'я і поливу не вигадуй.
```

## Дерево

```text
main.py
app/contracts/     готовий спільний шар
app/core/          людина 1, рушій
app/wiring/        людина 1, фасад
app/shell/         людина 2, екрани
app/garden/        людина 3, карта
app/knowledge/     людина 4, довідка і погода
app/storage/       людина 5, база
assets/plants/     необов'язкові картинки
docs/RULES.md
docs/ARCHITECTURE.md
tests/test_scaffold.py
```
