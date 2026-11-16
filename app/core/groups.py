"""Збирання горщиків одного виду в групу. Поріг — GROUP_MIN_POTS. Правила — docs/RULES.md, розділ «Групи»."""

from __future__ import annotations

from dataclasses import replace

from app.contracts.constants import GROUP_MIN_POTS
from app.contracts.ids import new_id
from app.contracts.models import CropGroup, Pot

GROUP_TITLE = "Група: {name}"


def _valid_group_id(pot: Pot, by_id: dict[str, CropGroup]) -> str | None:
    """Група лишається, лише якщо вона є серед existing і того ж виду, що й горщик."""
    if pot.group_id is None:
        return None
    group = by_id.get(pot.group_id)
    if group is None or group.species_id != pot.profile.species_id:
        return None
    return pot.group_id


class GroupBuilder:
    def suggest(
        self,
        pots: list[Pot],
        existing: list[CropGroup],
        titles: dict[str, str],
    ) -> tuple[list[CropGroup], list[Pot]]:
        by_id: dict[str, CropGroup] = {}
        for group in existing:
            by_id.setdefault(group.id, group)
        groups: list[CropGroup] = list(by_id.values())

        result = [replace(pot, group_id=_valid_group_id(pot, by_id)) for pot in pots]

        species_order: list[str] = []
        for pot in result:
            if pot.profile.species_id not in species_order:
                species_order.append(pot.profile.species_id)

        for species_id in species_order:
            free = [i for i, pot in enumerate(result) if pot.group_id is None and pot.profile.species_id == species_id]
            if not free:
                continue
            target = next((g for g in groups if g.species_id == species_id), None)
            if target is None:
                if len(free) < GROUP_MIN_POTS:
                    continue
                target = CropGroup(
                    id=new_id(),
                    zone_id=result[free[0]].zone_id,
                    species_id=species_id,
                    title=GROUP_TITLE.format(name=titles.get(species_id, species_id)),
                    pot_ids=(),
                    x=0.0,
                    y=0.0,
                )
                groups.append(target)
            for i in free:
                result[i] = replace(result[i], group_id=target.id)

        return [self._refresh(group, result) for group in groups], result

    @staticmethod
    def _refresh(group: CropGroup, pots: list[Pot]) -> CropGroup:
        """Склад і центр групи з живих горщиків. Порожня група тримає свій старий центр."""
        members = [pot for pot in pots if pot.group_id == group.id]
        if not members:
            return replace(group, pot_ids=())
        return replace(
            group,
            pot_ids=tuple(pot.id for pot in members),
            x=sum(pot.x for pot in members) / len(members),
            y=sum(pot.y for pot in members) / len(members),
        )
