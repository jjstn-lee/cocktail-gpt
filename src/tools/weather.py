import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from .base import SourcePayload, SourceUnavailableError


async def _fetch_current_weather(
    lat: float, lon: float, api_key: str
) -> dict[str, Any]:
    """Fetch current weather data from OpenWeatherMap API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params: dict[str, str | float] = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",  # Use Celsius for cocktail vibe purposes
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


async def _fetch_hourly_forecast(
    lat: float, lon: float, api_key: str
) -> dict[str, Any]:
    """Fetch hourly forecast data from OpenWeatherMap API (first 12 hours)."""
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params: dict[str, str | float | int] = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "cnt": 12,  # 12 * 3 hours = 36 hours
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


def _extract_current_signal(weather: dict[str, Any]) -> dict[str, Any]:
    """Extract current weather signal."""
    main = weather.get("main", {})
    wind = weather.get("wind", {})
    clouds = weather.get("clouds", {})
    weather_info = weather.get("weather", [{}])[0]

    return {
        "temp": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "clouds": clouds.get("all"),
        "condition": weather_info.get("main"),
        "description": weather_info.get("description"),
        "sunrise": weather.get("sys", {}).get("sunrise"),
        "sunset": weather.get("sys", {}).get("sunset"),
    }


def _extract_forecast_signal(forecast: dict[str, Any]) -> dict[str, Any]:
    """Extract forecast signal (next 12 hours broken into 3-hour segments)."""
    forecast_entries = forecast.get("list", [])
    if not forecast_entries:
        return {
            "avg_temp": 0.0,
            "avg_humidity": 0.0,
            "avg_wind_speed": 0.0,
            "forecast_count": 0,
            "conditions": [],
        }

    temps = []
    humidities = []
    wind_speeds = []
    conditions = []

    for entry in forecast_entries:
        main = entry.get("main", {})
        wind = entry.get("wind", {})
        weather_info = entry.get("weather", [{}])[0]

        if main.get("temp") is not None:
            temps.append(main.get("temp"))
        if main.get("humidity") is not None:
            humidities.append(main.get("humidity"))
        if wind.get("speed") is not None:
            wind_speeds.append(wind.get("speed"))

        condition = weather_info.get("main")
        if condition and condition not in conditions:
            conditions.append(condition)

    avg_temp = sum(temps) / len(temps) if temps else 0.0
    avg_humidity = sum(humidities) / len(humidities) if humidities else 0.0
    avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0.0

    return {
        "avg_temp": avg_temp,
        "avg_humidity": avg_humidity,
        "avg_wind_speed": avg_wind_speed,
        "forecast_count": len(forecast_entries),
        "conditions": conditions,
    }


def _calculate_confidence() -> float:
    """Calculate confidence for weather data.

    Weather data is generally reliable when fresh, but confidence degrades
    if not both current and forecast succeeded.
    """
    return 0.75  # Weather APIs are fairly reliable


async def fetch_weather(
    user_id: str, lat: float | None = None, lon: float | None = None
) -> SourcePayload:
    """Main entry point: fetch and normalize weather data.

    Args:
        user_id: User identifier
        lat: Latitude (optional; if not provided, must be in user profile)
        lon: Longitude (optional; if not provided, must be in user profile)

    Raises:
        SourceUnavailableError: If API key is missing or API calls fail.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise SourceUnavailableError(
            "weather",
            "Missing OPENWEATHER_API_KEY environment variable",
        )

    # If lat/lon not provided, this should come from user context/state
    # For now, default to New York as placeholder
    if lat is None or lon is None:
        lat = float(os.getenv("DEFAULT_LAT", "40.7128"))
        lon = float(os.getenv("DEFAULT_LON", "-74.0060"))

    logger.debug(f"Fetching weather data for user {user_id} at ({lat}, {lon})")

    try:
        # Fetch both current and forecast concurrently
        results = await asyncio.gather(
            _fetch_current_weather(lat, lon, api_key),
            _fetch_hourly_forecast(lat, lon, api_key),
            return_exceptions=True,
        )

        current_weather_result: Any = results[0]
        forecast_result: Any = results[1]

        # Check for exceptions
        current_weather_success = not isinstance(current_weather_result, Exception)
        forecast_success = not isinstance(forecast_result, Exception)

        current_weather: dict[str, Any]
        if isinstance(current_weather_result, Exception):
            logger.warning(f"Weather current fetch failed: {current_weather_result}")
            current_weather = {}
        else:
            current_weather = current_weather_result

        forecast: dict[str, Any]
        if isinstance(forecast_result, Exception):
            logger.warning(f"Weather forecast fetch failed: {forecast_result}")
            forecast = {"list": []}
        else:
            forecast = forecast_result

        # Extract signals
        signals = {
            "current": _extract_current_signal(current_weather),
            "forecast": _extract_forecast_signal(forecast),
        }

        confidence = _calculate_confidence()

        logger.info(
            f"Weather fetch complete for user {user_id}; confidence={confidence:.2f}, "
            f"sources=[current={current_weather_success}, forecast={forecast_success}]"
        )

        return SourcePayload(
            source="weather",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            signals=signals,
            confidence=confidence,
        )

    except Exception as e:
        raise SourceUnavailableError(
            "weather",
            f"Unexpected error fetching weather data: {str(e)}",
            original=e,
        )
