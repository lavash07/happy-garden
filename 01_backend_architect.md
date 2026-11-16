# Роль 1/5 — Backend Architect & Integration Lead

> Скопируй этот файл целиком в свою AI-модель. Твоя задача — реализовать центральный backend-каркас Growverse и обеспечить интеграцию модулей. Ты не пишешь весь frontend и не забираешь себе специализированные алгоритмы остальных участников.


# Growverse — общий контекст проекта

## Что строим

Growverse — веб-приложение для управления реальным огородом, теплицей или небольшой фермой через её интерактивную цифровую копию.

Пользователь создаёт виртуальную территорию, добавляет культуры (например, огурцы и помидоры), указывает сорт, дату посадки, место выращивания и условия. Приложение показывает растения на виртуальной карте, оценивает стадию роста, хранит состояние, показывает погоду для локации и формирует практические задачи по уходу.

Это MVP для хакатона, а не промышленная агрономическая система. Расчёты роста и состояния должны быть честно обозначены как приблизительные. Нельзя выдавать демонстрационные/введённые вручную значения за реальные измерения датчиков.

## Главный демонстрационный сценарий

1. Открыть приложение.
2. Создать ферму/теплицу с названием, типом и локацией.
3. Добавить огурец или помидор: культура, сорт, дата посадки, способ выращивания, тип почвы и координаты на виртуальной территории.
4. Увидеть растение на виртуальной карте.
5. Открыть карточку растения и увидеть стадию роста, примерный прогресс, здоровье и условия.
6. Открыть погоду фермы и увидеть прогноз.
7. Получить хотя бы одну рекомендацию/задачу по уходу.
8. Обновить страницу и убедиться, что данные сохранились.

## Стек (не менять без согласования)

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- SQLite
- HTML, CSS, vanilla JavaScript
- Canvas 2D для интерактивной карты
- Open-Meteo API для погоды (без API-ключа для обычного прогноза)
- pytest для тестов

Не добавляйте React/Vue, Docker, Celery, Redis, авторизацию через OAuth или другие тяжёлые технологии без явной необходимости. Цель — надёжный MVP, который можно запустить локально.

## Общие правила разработки

1. Python — основа бизнес-логики.
2. Backend является источником истины для сохранённых данных и расчётов.
3. Frontend отвечает за отображение и взаимодействие, но не реализует агрономические расчёты.
4. Все данные между frontend и backend передаются через JSON и описанные ниже REST endpoints.
5. Не переименовывать поля, endpoints, enum-значения и функции из этого документа.
6. Не создавать дублирующие модели или альтернативные форматы данных.
7. Не использовать реальные данные датчиков, если датчиков нет. Неизвестные показатели обозначать `null` или явно помечать как оценку.
8. Для внешних API предусмотреть timeout, обработку ошибок и fallback-состояние.
9. Не хардкодить секреты и API-ключи.
10. Писать понятный код с type hints, небольшими функциями и обработкой ошибок.
11. Не добавлять функциональность, не относящуюся к назначенной роли.
12. Если обнаружено противоречие в контракте, не менять его молча: описать проблему и предложить согласованное изменение.
13. Не перезаписывать чужие файлы. Работать только в списке разрешённых файлов.
14. В конце выдать список созданных файлов, инструкции запуска, тесты и известные ограничения.

## Единые сущности и форматы данных

### Farm

```json
{
  "id": 1,
  "name": "Моя теплица",
  "farm_type": "greenhouse",
  "location_name": "Kyiv, Ukraine",
  "latitude": 50.4501,
  "longitude": 30.5234,
  "area_m2": 40.0,
  "created_at": "2026-11-16T10:00:00"
}
```

Допустимые `farm_type`:
- `greenhouse`
- `garden`
- `farm`
- `orchard`
- `balcony`

### Plant

```json
{
  "id": 101,
  "farm_id": 1,
  "name": "Cucumber",
  "variety": "Masha F1",
  "planted_at": "2026-11-01",
  "growing_method": "greenhouse",
  "soil_type": "loam",
  "quantity": 3,
  "position_x": 120,
  "position_y": 240,
  "growth_stage": "seedling",
  "growth_progress": 25.0,
  "health_score": 87,
  "status": "healthy",
  "estimated_harvest_date": "2026-12-20"
}
```

Допустимые `growing_method`:
- `open_ground`
- `greenhouse`
- `container`

Допустимые `soil_type`:
- `loam`
- `sandy`
- `clay`
- `peat`
- `mixed`
- `unknown`

Допустимые `growth_stage`:
- `seed`
- `seedling`
- `vegetative`
- `flowering`
- `fruiting`
- `harvest`
- `completed`

Допустимые `status`:
- `healthy`
- `attention`
- `critical`
- `unknown`

### Weather

```json
{
  "farm_id": 1,
  "current": {
    "temperature_c": 12.5,
    "relative_humidity": 70,
    "precipitation_mm": 0.0,
    "wind_speed_kmh": 8.0
  },
  "daily": [
    {
      "date": "2026-11-16",
      "temperature_max_c": 14.0,
      "temperature_min_c": 5.0,
      "precipitation_sum_mm": 2.0,
      "precipitation_probability_max": 40
    }
  ],
  "source": "Open-Meteo",
  "is_demo": false
}
```

### Task

```json
{
  "id": 501,
  "farm_id": 1,
  "plant_id": 101,
  "title": "Проверить влажность почвы",
  "description": "Проверьте влажность грунта перед следующим поливом.",
  "priority": "medium",
  "due_date": "2026-11-17",
  "completed": false,
  "source": "care_engine"
}
```

Допустимые `priority`: `low`, `medium`, `high`, `critical`.

## REST API — фиксированный контракт

Base URL: `http://127.0.0.1:8000`

### Farms
- `GET /api/farms` — список ферм.
- `POST /api/farms` — создать ферму.
- `GET /api/farms/{farm_id}` — получить ферму.
- `GET /api/farms/{farm_id}/overview` — ферма, растения, задачи и краткая сводка.

### Plants
- `GET /api/farms/{farm_id}/plants` — растения фермы.
- `POST /api/farms/{farm_id}/plants` — добавить растение.
- `GET /api/plants/{plant_id}` — получить растение с расчётными полями.
- `PATCH /api/plants/{plant_id}` — обновить редактируемые поля/позицию.

### Weather and care
- `GET /api/farms/{farm_id}/weather` — текущая погода и прогноз.
- `GET /api/farms/{farm_id}/tasks` — задачи фермы.
- `POST /api/tasks/{task_id}/complete` — отметить задачу выполненной.
- `POST /api/farms/{farm_id}/care/recalculate` — пересчитать рекомендации/задачи.

### System
- `GET /api/health` — `{"status":"ok"}`.

### Создание фермы — POST body

```json
{
  "name": "Моя теплица",
  "farm_type": "greenhouse",
  "location_name": "Kyiv, Ukraine",
  "latitude": 50.4501,
  "longitude": 30.5234,
  "area_m2": 40.0
}
```

### Создание растения — POST body

```json
{
  "name": "Cucumber",
  "variety": "Masha F1",
  "planted_at": "2026-11-01",
  "growing_method": "greenhouse",
  "soil_type": "loam",
  "quantity": 3,
  "position_x": 120,
  "position_y": 240
}
```

### Обновление растения — PATCH body

Разрешены только:
`variety`, `planted_at`, `growing_method`, `soil_type`, `quantity`, `position_x`, `position_y`.

## Ошибки API

Использовать стандартные HTTP-коды и FastAPI `HTTPException`.
Формат ошибки FastAPI по умолчанию допустим. Frontend обязан показывать человеку понятное сообщение, если запрос не удался.

## Общая структура репозитория

```text
growverse/
├── README.md
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── api/
│   └── services/
└── frontend/
    ├── index.html
    ├── styles/
    ├── js/
    └── assets/
```

## Критерий готовности всего продукта

Проект считается собранным, если команда может запустить backend и frontend, создать ферму, добавить растение, увидеть его на карте, открыть карточку с расчётами, получить погоду и увидеть задачу по уходу. Все критические действия должны работать, а не быть только нарисованными.


## Твоя ответственность

Ты владелец центральной backend-инфраструктуры:
- FastAPI application и запуск.
- SQLite и SQLAlchemy.
- Общие SQLAlchemy-модели и Pydantic-схемы.
- REST endpoints из общего контракта.
- Подключение сервисов Plant Intelligence и Weather & Care.
- CORS для локального frontend.
- Инициализация базы и демонстрационные данные (по желанию).
- Интеграционные тесты и инструкция запуска.

## Разрешённые файлы

- `backend/main.py`
- `backend/database.py`
- `backend/models.py`
- `backend/schemas.py`
- `backend/api/__init__.py`
- `backend/api/farms.py`
- `backend/api/plants.py`
- `backend/api/weather.py`
- `backend/api/tasks.py`
- `backend/services/__init__.py`
- `backend/tests/test_api.py`
- `requirements.txt`
- `README.md`

Можешь создавать дополнительные файлы внутри `backend/api/` и `backend/tests/`, если это необходимо. Не переписывай `backend/services/growth/` и `backend/services/weather_care/` — это зоны владельцев ролей 3 и 4.

## Обязательные модели

Создай SQLAlchemy-модели Farm, Plant и CareTask по полям общего контракта. Используй `datetime`/`date` корректно, а при выдаче API сериализуй их в ISO-формат. У Farm может быть много Plant и CareTask. У Plant может быть много CareTask. Удали каскадно связанные записи при удалении фермы, если реализуешь удаление.

Важно: не добавляй поля, которые меняют публичный контракт, без необходимости. Внутренние поля допустимы, если они не ломают API.

## Обязательные endpoints

Реализуй все endpoints из раздела REST API общего контекста:
- farms list/create/get/overview;
- plants list/create/get/patch;
- weather;
- tasks list/complete;
- care recalculate;
- health.

Для endpoints, принадлежащих сервисным модулям, вызывай функции через согласованные интерфейсы ниже. Если сервис ещё не готов, используй временную заглушку с тем же интерфейсом.

## Межмодульные Python-интерфейсы

### Plant Intelligence (роль 3)

Ожидаемые импорты:

```python
from backend.services.growth.engine import (
    calculate_plant_metrics,
    get_plant_catalog,
)
```

`calculate_plant_metrics(plant_data: dict, current_date: date) -> dict` возвращает:

```python
{
    "growth_stage": "seedling",
    "growth_progress": 25.0,
    "health_score": 87,
    "status": "healthy",
    "estimated_harvest_date": "2026-12-20"
}
```

`get_plant_catalog() -> list[dict]` возвращает доступные культуры/сорта и базовые требования.

### Weather & Care (роль 4)

Ожидаемые импорты:

```python
from backend.services.weather_care.service import (
    get_farm_weather,
    generate_care_tasks,
)
```

`get_farm_weather(latitude: float, longitude: float) -> dict` возвращает Weather-формат общего контракта без `farm_id`; backend добавляет `farm_id`.

`generate_care_tasks(farm: dict, plants: list[dict], weather: dict) -> list[dict]` возвращает список Task-словарей без `id`; backend сохраняет задачи в БД и назначает ID.

Если сервисный модуль пока отсутствует, создай временную реализацию в своём коде или отдельный adapter, но не меняй имена и сигнатуры.

## Важные требования к backend

- Используй dependency session для SQLAlchemy.
- Не выполняй синхронный долгий сетевой запрос без timeout.
- Внешний погодный API не должен ломать всё приложение при недоступности: верни контролируемую ошибку либо явно помеченный demo fallback.
- Валидация входных данных через Pydantic.
- Не возвращай SQLAlchemy-объекты напрямую.
- CORS разреши для локального dev frontend.
- Все endpoints должны иметь понятные response models, где возможно.
- Добавь `GET /api/health`.
- Backend должен запускаться командой `uvicorn backend.main:app --reload`.

## Тесты

Покрой минимум:
1. Health endpoint.
2. Создание фермы и получение списка.
3. Добавление растения в ферму.
4. Получение растений фермы.
5. Ошибка для несуществующего farm_id.
6. Отметка задачи выполненной.

Используй отдельную тестовую SQLite-базу или dependency override, чтобы тесты не портили локальные данные.

## Definition of Done

- Backend запускается по указанной команде.
- Все endpoints существуют.
- Форматы ответов соответствуют общему контракту.
- Вызовы сервисов сделаны через согласованные интерфейсы.
- Тесты проходят.
- README объясняет запуск backend и frontend.
- Ты не изменял публичные API-контракты.

## Формат твоего результата

Верни:
1. Краткое описание архитектуры.
2. Полное содержимое каждого созданного файла с путём.
3. Команды установки и запуска.
4. Результаты тестов (если реально запускал; не выдумывай).
5. Список незавершённых интеграций и точные инструкции для владельцев ролей 3 и 4.

Если среда позволяет создавать файлы в общем репозитории — создавай только разрешённые файлы. Если нет — выведи файлы по одному в отдельных code blocks с путями.
