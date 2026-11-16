"""Open-Meteo: безкоштовно, без ключа. httpx імпортуй усередині alerts, щоб пакет жив без мережі на старті.

Погода лише повертає попередження. Вологу горщиків вона не змінює.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.contracts.labels import OFFLINE_WEATHER
from app.contracts.models import AlertSeverity, SpeciesProfile, WeatherAlert

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = "temperature_2m_min,temperature_2m_max,precipitation_sum,weather_code,wind_gusts_10m_max"
TIMEOUT_S = 8.0
FORECAST_TTL_S = 15 * 60  # прогноз не змінюється щохвилини, а меню відкриває зону часто
DAYS = 2

FROST_C = 2
HEAT_C = 32
RAIN_MM = 10
WIND_KMH = 60
COLD_MARGIN_C = 3

# Коди WMO, які віддає Open-Meteo.
THUNDER = {95}
THUNDER_HAIL = {96, 99}
SNOW = {71, 73, 75, 77, 85, 86}

CALM_TITLE = "Погода спокійна"


def _alert(severity: AlertSeverity, title: str, advice: str, now: datetime) -> WeatherAlert:
    return WeatherAlert(severity=severity, title=title, advice=advice, starts_at=now)


def _first(values: Any) -> list[float]:
    """Перші DAYS значень, без None."""
    return [float(v) for v in list(values or [])[:DAYS] if v is not None]


def alerts_from_daily(daily: dict, species: SpeciesProfile | None, now: datetime) -> list[WeatherAlert]:
    """Попередження за перші дві доби. Чиста функція: тести не ходять у мережу."""
    lows = _first(daily.get("temperature_2m_min"))
    highs = _first(daily.get("temperature_2m_max"))
    rain = _first(daily.get("precipitation_sum"))
    codes = {int(code) for code in _first(daily.get("weather_code"))}
    gusts = _first(daily.get("wind_gusts_10m_max"))

    out: list[WeatherAlert] = []
    frost = bool(lows) and min(lows) <= FROST_C
    if codes & THUNDER_HAIL:
        out.append(_alert(AlertSeverity.DANGER, "Гроза з градом", "Сховай горщики під дах або накрий", now))
    elif codes & THUNDER:
        out.append(_alert(AlertSeverity.DANGER, "Гроза", "Прибери легкі горщики під дах і не поливай перед грозою", now))
    if frost:
        out.append(_alert(AlertSeverity.DANGER, "Мороз", "Накрий рослини або занеси горщики в тепло", now))
    if codes & SNOW:
        out.append(_alert(AlertSeverity.WARNING, "Сніг", "Струси сніг з укриттів і бережи горщики від холоду", now))
    if highs and max(highs) >= HEAT_C:
        out.append(_alert(AlertSeverity.WARNING, "Спека", "Полий зранку і притіни", now))
    if gusts and max(gusts) >= WIND_KMH:
        out.append(_alert(AlertSeverity.WARNING, "Сильний вітер", "Підв'яжи високі рослини і закрий кватирки", now))
    if species is not None and lows and not frost and min(lows) < species.temp_c[0] - COLD_MARGIN_C:
        out.append(
            _alert(
                AlertSeverity.WARNING,
                f"Холодно для культури «{species.name}»",
                "Поки що не тримай рослину просто неба",
                now,
            )
        )
    if rain and max(rain) >= RAIN_MM:
        out.append(_alert(AlertSeverity.INFO, "Дощ", "Сьогодні можна не поливати", now))
    return out


def calm_alert(daily: dict, now: datetime) -> WeatherAlert:
    """Коли попереджень немає: коротко, яка сьогодні температура."""
    lows, highs = _first(daily.get("temperature_2m_min")), _first(daily.get("temperature_2m_max"))
    if lows and highs:
        advice = f"Сьогодні від {lows[0]:+.0f}° до {highs[0]:+.0f}°"
    else:
        advice = "Небезпечних явищ не очікується"
    return _alert(AlertSeverity.INFO, CALM_TITLE, advice, now)


class WeatherService:
    def __init__(self) -> None:
        self._geo_cache: dict[str, tuple[float, float]] = {}
        self._daily_cache: dict[tuple[float, float], tuple[float, dict]] = {}

    def alerts(self, territory: str, species: SpeciesProfile, now: datetime) -> list[WeatherAlert]:
        """Попередження для місцевості. Будь-яка мережева помилка — одне info з OFFLINE_WEATHER."""
        place = " ".join((territory or "").split())
        if not place:
            return []
        try:
            daily = self._daily(place)
        except Exception:  # noqa: BLE001 — без мережі застосунок працює далі
            return [_alert(AlertSeverity.INFO, "Погода", OFFLINE_WEATHER, now)]
        if daily is None:
            return [_alert(AlertSeverity.INFO, "Погода", f"Не знайшли місцевість «{place}»", now)]
        return alerts_from_daily(daily, species, now) or [calm_alert(daily, now)]

    def _daily(self, place: str) -> dict | None:
        import httpx

        key = place.casefold()
        if key not in self._geo_cache:
            response = httpx.get(
                GEOCODE_URL,
                params={"name": place, "count": 1, "language": "uk", "format": "json"},
                timeout=TIMEOUT_S,
            )
            response.raise_for_status()
            results = response.json().get("results") or []
            if not results:
                return None
            self._geo_cache[key] = (float(results[0]["latitude"]), float(results[0]["longitude"]))
        point = self._geo_cache[key]

        cached = self._daily_cache.get(point)
        if cached and time.monotonic() - cached[0] < FORECAST_TTL_S:
            return cached[1]
        response = httpx.get(
            FORECAST_URL,
            params={
                "latitude": point[0],
                "longitude": point[1],
                "daily": DAILY_FIELDS,
                "timezone": "auto",
                "forecast_days": DAYS,
            },
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        daily = response.json().get("daily") or {}
        self._daily_cache[point] = (time.monotonic(), daily)
        return daily
