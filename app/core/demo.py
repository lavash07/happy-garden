"""Перевірка, що ядро працює. Запуск: python -m app.core.demo"""

from datetime import timedelta

from app.contracts.labels import MOOD_LABELS, STAGE_LABELS, as_percent
from app.contracts.models import CareAction
from app.contracts.samples import PLANTED, sample_species, sample_zone_view
from app.core.care import CarePlanner
from app.core.growth import GrowthEngine


def main() -> None:
    engine = GrowthEngine()
    species = sample_species()[0]
    profile = sample_zone_view().cards[0].pot.profile
    marks = engine.timeline(profile, species)
    print(f"календар: {marks[0].label} з дня {marks[0].starts_on_day}")

    pot, planted = engine.plant("zone-demo", profile, 400, 500, species)
    events = [planted]
    for day in range(1, 40):
        events.append(engine.make_event(pot.id, CareAction.WATER, PLANTED + timedelta(days=day)))
    for day in (0, 7, 20, 39):
        now = PLANTED + timedelta(days=day)
        state = engine.advance(pot, species, events, now)
        plan = CarePlanner().plan(state, species, events, now)
        print(
            f"день {day:>2}: {STAGE_LABELS[state.stage]} {as_percent(state.stage_progress)}%, "
            f"волога {as_percent(state.moisture)}%, здоров'я {as_percent(state.health)}%, "
            f"{MOOD_LABELS[state.mood]}; полив до {plan.next_water_at:%d.%m %H:%M}"
        )


if __name__ == "__main__":
    main()
