# Що додала людина 1 в app/garden

`farm.py` — `FarmBench`, сцена фазенди для `main.py`. Твій `bench.py` не чіпали, він запускається через `flet run app/garden/demo.py`.

- Реалізує `GardenCanvas` (`control`, `show`, `spawn_point`), конструктор як у `GardenMap`. Дані бере лише з `ZoneView`, без власної моделі горщика.
- Фон — `assets/backgrounds/farm.jpg` (копія `bg_for site.png`, 2560 px). Горщики стоять на стільниці з фото, на телефоні зменшуються, щоб вміститися.
- Картинку горщика вибирає `app.contracts.pictures.pot_picture(species_id, stage)` — та сама таблиця для меню. Кадри — `assets/pots/`, їх робить `scripts/render_pots.py`.
- Якщо задати `canvas.on_add`, на вільному місці столу з'являється «+». Оболонка відкриває форму посадки.

Чому окремий `render_pots.py`: у `render_models.py` масштаб береться з нижніх 18% вершин, тому в рендерах горщики різного розміру, а `tomato_stage3`, `potato`, `carrot_1/2` обрізані зверху. `render_pots.py` міряє ширину горщика за теракотовими вершинами і бере спільну висоту кадру для всіх моделей. Твій скрипт і `assets/models` не чіпали — їх і далі бере `bench.py`.
