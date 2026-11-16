"""Порядок таблиці друзів один на всіх."""

from app.contracts.models import LeaderboardRow


def sort_leaderboard(rows: list[LeaderboardRow]) -> list[LeaderboardRow]:
    return sorted(rows, key=lambda row: (-row.points, 0 if row.is_you else 1, row.nickname.casefold()))
