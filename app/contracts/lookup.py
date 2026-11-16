"""Пошук картки горщика всередині вже зібраного ZoneView."""

from app.contracts.models import Pot, PotCard, ZoneView


def pots_of(view: ZoneView) -> tuple[Pot, ...]:
    return tuple(card.pot for card in view.cards)


def card_for(view: ZoneView, pot_id: str) -> PotCard | None:
    for card in view.cards:
        if card.pot.id == pot_id:
            return card
    return None
