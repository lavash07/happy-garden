"""Правила погоди без мережі: лише alerts_from_daily і злиття попереджень зони."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.contracts.models import AlertSeverity, WeatherAlert
from app.contracts.samples import sample_species
from app.knowledge.weather import CALM_TITLE, WeatherService, alerts_from_daily, calm_alert
from app.wiring.preview import merge_alerts

NOW = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)
CUCUMBER = sample_species()[0]  # temp_c від 20


def day(lo=(10, 10), hi=(18, 18), rain=(0, 0), code=(1, 1), gust=(10, 10)) -> dict:
    return {
        "temperature_2m_min": list(lo),
        "temperature_2m_max": list(hi),
        "precipitation_sum": list(rain),
        "weather_code": list(code),
        "wind_gusts_10m_max": list(gust),
    }


def titles(alerts: list[WeatherAlert]) -> list[str]:
    return [a.title for a in alerts]


class WeatherRulesTests(unittest.TestCase):
    def test_frost(self) -> None:
        alerts = alerts_from_daily(day(lo=(5, 1.5)), CUCUMBER, NOW)
        frost = next(a for a in alerts if a.title == "Мороз")
        self.assertEqual(frost.severity, AlertSeverity.DANGER)
        self.assertEqual(frost.starts_at, NOW)
        self.assertNotIn("Холодно", " ".join(titles(alerts)))  # мороз уже сказав головне

    def test_heat_and_rain(self) -> None:
        alerts = alerts_from_daily(day(lo=(21, 21), hi=(33, 30), rain=(0, 12)), CUCUMBER, NOW)
        self.assertEqual(titles(alerts), ["Спека", "Дощ"])
        self.assertEqual(alerts[1].severity, AlertSeverity.INFO)

    def test_thunder_hail_wind(self) -> None:
        self.assertIn("Гроза", titles(alerts_from_daily(day(code=(3, 95)), None, NOW)))
        self.assertIn("Гроза з градом", titles(alerts_from_daily(day(code=(99, 1)), None, NOW)))
        wind = alerts_from_daily(day(gust=(20, 70)), None, NOW)
        self.assertEqual(titles(wind), ["Сильний вітер"])

    def test_cold_for_species(self) -> None:
        alerts = alerts_from_daily(day(lo=(15, 12)), CUCUMBER, NOW)
        self.assertEqual(titles(alerts), ["Холодно для культури «Огірок»"])
        self.assertEqual(alerts_from_daily(day(lo=(15, 12)), None, NOW), [])

    def test_only_first_two_days(self) -> None:
        self.assertEqual(alerts_from_daily(day(lo=(10, 10, -5)), None, NOW), [])

    def test_calm_text(self) -> None:
        calm = calm_alert(day(lo=(3, 4), hi=(9, 8)), NOW)
        self.assertEqual(calm.title, CALM_TITLE)
        self.assertIn("+3°", calm.advice)

    def test_empty_territory(self) -> None:
        self.assertEqual(WeatherService().alerts("   ", CUCUMBER, NOW), [])


class MergeTests(unittest.TestCase):
    def test_dedup_and_order(self) -> None:
        rain = WeatherAlert(AlertSeverity.INFO, "Дощ", "a", NOW)
        frost = WeatherAlert(AlertSeverity.DANGER, "Мороз", "b", NOW)
        calm = WeatherAlert(AlertSeverity.INFO, CALM_TITLE, "c", NOW)
        merged = merge_alerts([[rain, calm], [frost, rain]])
        self.assertEqual(titles(list(merged)), ["Мороз", "Дощ"])
        self.assertEqual(merge_alerts([[calm], [calm]]), (calm,))


if __name__ == "__main__":
    unittest.main()
