"""Нормативний календар з довідки. Без поправки на ґрунт і пропущені поливи."""

from app.contracts.labels import STAGE_LABELS
from app.contracts.models import STAGE_ORDER, SpeciesProfile, StageMark


def ideal_timeline(species: SpeciesProfile) -> tuple[StageMark, ...]:
    day = 0
    marks: list[StageMark] = []
    for stage in STAGE_ORDER:
        marks.append(StageMark(stage=stage, starts_on_day=day, label=STAGE_LABELS[stage]))
        day += int(species.stage_days[stage.value])
    return tuple(marks)
