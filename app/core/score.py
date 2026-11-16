"""Очки грядки для екрана друзів. Формула — docs/RULES.md, розділ «Очки»."""

from __future__ import annotations

from app.contracts.models import (
    CareAction,
    CareEvent,
    FarmScore,
    Friend,
    GrowthStage,
    LeaderboardRow,
    Pot,
    Zone,
)
from app.contracts.ranking import sort_leaderboard


class Scoreboard:
    def score_zone(
        self,
        zone: Zone,
        pots: list[Pot],
        events: list[CareEvent],
        nickname: str,
    ) -> FarmScore:
        if not pots:
            return FarmScore(zone_id=zone.id, nickname=nickname, health=0.0, ripe_count=0, points=0)
        health = sum(pot.health for pot in pots) / len(pots)
        ripe_count = sum(1 for pot in pots if pot.stage == GrowthStage.RIPE)
        harvests = sum(1 for event in events if event.action == CareAction.HARVEST)
        points = round(100 * health + 25 * ripe_count + 15 * harvests)
        return FarmScore(
            zone_id=zone.id,
            nickname=nickname,
            health=health,
            ripe_count=ripe_count,
            points=int(points),
        )

    def leaderboard(self, you: FarmScore, friends: list[Friend]) -> list[LeaderboardRow]:
        rows = [LeaderboardRow(nickname=you.nickname, points=you.points, is_you=True)]
        rows.extend(LeaderboardRow(nickname=f.nickname, points=f.points, is_you=False) for f in friends)
        return sort_leaderboard(rows)
