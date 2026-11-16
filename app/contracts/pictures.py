"""Картинки горщиків з 3D-моделей. Одна таблиця для меню (app/shell) і сцени (app/garden).

PNG рендерить scripts/render_pots.py у assets/pots (горщик однакового розміру в усіх кадрах).
Шляхи — відносно assets/.
Якщо для культури картинки немає, функція повертає None, і екран малює glyph з довідки.
"""

from __future__ import annotations

from app.contracts.models import STAGE_ORDER, GrowthStage


def _frames(stem: str, count: int, pattern: str = "{stem}_stage{n}") -> tuple[str, ...]:
    return tuple(f"pots/{pattern.format(stem=stem, n=n)}.png" for n in range(1, count + 1))


POT_PICTURES: dict[str, tuple[str, ...]] = {
    "cucumber": _frames("cute_cucumber", 3),
    "tomato": _frames("tomato", 3),
    "pepper": _frames("cute_pepper", 3),
    "potato": _frames("potato", 3),
    "carrot": _frames("carrot", 4, "{stem}_{n}"),
    "onion": _frames("onion", 4, "{stem}_{n}"),
    "pumpkin": _frames("pumpkin", 4, "{stem}_{n}"),
    "zucchini": _frames("cute_zucchini", 4),
    "pea": _frames("cute_pea", 4),
    "corn": _frames("cute_corn", 4),
}

# Кадр scripts/render_pots.py: 400×629, дно горщика на 605 px. Ширина горщика — 0.62 кадру.
PICTURE_RATIO = 400 / 629
PICTURE_FOOT = 605 / 629
PICTURE_POT_SHARE = 0.62


def pot_picture(species_id: str, stage: GrowthStage) -> str | None:
    """Кадр для етапу: етапи рівномірно розкладені на наявні картинки. Зібраний — перший кадр."""
    frames = POT_PICTURES.get(species_id)
    if not frames:
        return None
    if stage == GrowthStage.HARVESTED or len(frames) == 1:
        return frames[0]
    position = STAGE_ORDER.index(GrowthStage(stage)) / (len(STAGE_ORDER) - 1)
    return frames[min(len(frames) - 1, int(position * (len(frames) - 1) + 0.5))]
