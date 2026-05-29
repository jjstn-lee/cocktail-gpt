import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.tools.base import SourceUnavailableError
from src.tools.weather import (
    _calculate_confidence,
    _extract_current_signal,
    _extract_forecast_signal,
    _fetch_current_weather,
    _fetch_hourly_forecast,
    fetch_weather,
)


@pytest.fixture
def mock_current_weather_response() -> dict:
    """Mock response from OpenWeatherMap current weather endpoint."""
    return {
        "coord": {"lon": -74.006, "lat": 40.7128},
        "weather": [
            {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
        ],
        "main": {
            "temp": 18.5,
            "feels_like": 17.2,
            "temp_min": 16.1,
            "temp_max": 20.3,
            "pressure": 1013,
            "humidity": 65,
        },
        "wind": {"speed": 4.5, "deg": 230},
        "clouds": {"all": 10},
        "dt": 1000000000,
        "sys": {
            "type": 1,
            "id": 4610,
            "country": "US",
            "sunrise": 1000000000,
            "sunset": 1000050000,
        },
        "timezone": -14400,
        "id": 5128581,
        "name": "New York",
        "cod": 200,
    }


@pytest.fixture
def mock_forecast_response() -> dict:
    """Mock response from OpenWeatherMap forecast endpoint."""
    return {
        "cod": "200",
        "message": 0,
        "cnt": 12,
        "list": [
            {
                "dt": 1000000000 + i * 10800,
                "main": {
                    "temp": 18.5 + i * 0.5,
                    "feels_like": 17.2 + i * 0.5,
                    "temp_min": 16.1 + i * 0.5,
                    "temp_max": 20.3 + i * 0.5,
                    "pressure": 1013 - i,
                    "humidity": 65 - i,
                },
                "weather": [
                    {
                        "id": 800 + i % 3,
                        "main": ["Clear", "Clouds", "Rain"][i % 3],
                        "description": ["clear sky", "overcast clouds", "light rain"][
                            i % 3
                        ],
                        "icon": ["01d", "04d", "10d"][i % 3],
                    }
                ],
                "clouds": {"all": 10 + i * 5},
                "wind": {"speed": 4.5 + i * 0.2, "deg": 230},
                "visibility": 10000,
                "pop": i * 0.1,
                "sys": {"pod": "d"},
            }
            for i in range(12)
        ],
        "city": {
            "id": 5128581,
            "name": "New York",
            "coord": {"lat": 40.7128, "lon": -74.006},
            "country": "US",
            "population": 8000000,
            "timezone": -14400,
        },
    }


class TestExtractCurrentSignal:
    """Test extraction of current weather signals."""

    def test_extract_current_signal_full(self, mock_current_weather_response):
        """Test extracting signal from complete current weather response."""
        signal = _extract_current_signal(mock_current_weather_response)

        assert signal["temp"] == 18.5
        assert signal["feels_like"] == 17.2
        assert signal["humidity"] == 65
        assert signal["pressure"] == 1013
        assert signal["wind_speed"] == 4.5
        assert signal["clouds"] == 10
        assert signal["condition"] == "Clear"
        assert signal["description"] == "clear sky"

    def test_extract_current_signal_minimal(self):
        """Test extracting signal from minimal weather response."""
        minimal_response = {}
        signal = _extract_current_signal(minimal_response)

        assert signal["temp"] is None
        assert signal["humidity"] is None
        assert signal["condition"] is None

    def test_extract_current_signal_partial(self):
        """Test extracting signal from partial weather response."""
        partial_response = {
            "main": {"temp": 20.0, "humidity": 70},
            "weather": [{"main": "Sunny"}],
        }
        signal = _extract_current_signal(partial_response)

        assert signal["temp"] == 20.0
        assert signal["humidity"] == 70
        assert signal["condition"] == "Sunny"
        assert signal["wind_speed"] is None


class TestExtractForecastSignal:
    """Test extraction of forecast signals."""

    def test_extract_forecast_signal_full(self, mock_forecast_response):
        """Test extracting signal from complete forecast response."""
        signal = _extract_forecast_signal(mock_forecast_response)

        assert "avg_temp" in signal
        assert "avg_humidity" in signal
        assert "avg_wind_speed" in signal
        assert signal["forecast_count"] == 12
        assert len(signal["conditions"]) > 0

    def test_extract_forecast_signal_empty(self):
        """Test extracting signal from empty forecast response."""
        empty_response = {"list": []}
        signal = _extract_forecast_signal(empty_response)

        assert signal["avg_temp"] == 0.0
        assert signal["avg_humidity"] == 0.0
        assert signal["avg_wind_speed"] == 0.0
        assert signal["forecast_count"] == 0
        assert signal["conditions"] == []

    def test_extract_forecast_signal_missing_keys(self):
        """Test extracting signal when forecast entries are missing keys."""
        response = {
            "list": [
                {"main": {"temp": 20.0}},  # Missing humidity
                {"wind": {"speed": 5.0}},  # Missing temp
                {},  # Completely empty
            ]
        }
        signal = _extract_forecast_signal(response)

        assert signal["forecast_count"] == 3
        # Avg temp should be 20.0 / 1 = 20.0 (only one entry with temp)
        assert signal["avg_temp"] == 20.0
        # Avg wind speed should be 5.0 / 1 = 5.0
        assert signal["avg_wind_speed"] == 5.0


class TestCalculateConfidence:
    """Test confidence calculation."""

    def test_calculate_confidence(self):
        """Test that confidence is always 0.75 for weather data."""
        confidence = _calculate_confidence()
        assert confidence == 0.75


class TestFetchCurrentWeather:
    """Test fetching current weather."""

    @pytest.mark.asyncio
    async def test_fetch_current_weather_success(self, mock_current_weather_response):
        """Test successful current weather fetch."""
        with patch("src.tools.weather.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_current_weather_response
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_client_class.return_value = mock_client

            result = await _fetch_current_weather(40.7128, -74.006, "test_key")

            assert result == mock_current_weather_response
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_current_weather_http_error(self):
        """Test current weather fetch with HTTP error."""
        with patch("src.tools.weather.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await _fetch_current_weather(40.7128, -74.006, "test_key")


class TestFetchHourlyForecast:
    """Test fetching hourly forecast."""

    @pytest.mark.asyncio
    async def test_fetch_hourly_forecast_success(self, mock_forecast_response):
        """Test successful forecast fetch."""
        with patch("src.tools.weather.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_forecast_response
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_client_class.return_value = mock_client

            result = await _fetch_hourly_forecast(40.7128, -74.006, "test_key")

            assert result == mock_forecast_response
            mock_client.get.assert_called_once()


class TestFetchWeather:
    """Test the main fetch_weather entry point."""

    @pytest.mark.asyncio
    async def test_fetch_weather_success(
        self, mock_current_weather_response, mock_forecast_response
    ):
        """Test successful weather fetch."""
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
            with patch(
                "src.tools.weather._fetch_current_weather"
            ) as mock_current, patch(
                "src.tools.weather._fetch_hourly_forecast"
            ) as mock_forecast:
                mock_current.return_value = mock_current_weather_response
                mock_forecast.return_value = mock_forecast_response

                result = await fetch_weather("user123", 40.7128, -74.006)

                assert result["source"] == "weather"
                assert result["fetched_at"]
                assert result["signals"]["current"]["temp"] == 18.5
                assert result["signals"]["forecast"]["forecast_count"] == 12
                assert result["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_fetch_weather_missing_api_key(self):
        """Test weather fetch fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SourceUnavailableError) as exc_info:
                await fetch_weather("user123", 40.7128, -74.006)

            assert exc_info.value.source == "weather"
            assert "OPENWEATHER_API_KEY" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_fetch_weather_default_location(
        self, mock_current_weather_response, mock_forecast_response
    ):
        """Test weather fetch uses default location."""
        with patch.dict(
            os.environ,
            {
                "OPENWEATHER_API_KEY": "test_key",
                "DEFAULT_LAT": "51.5074",
                "DEFAULT_LON": "-0.1278",
            },
        ):
            with patch(
                "src.tools.weather._fetch_current_weather"
            ) as mock_current, patch(
                "src.tools.weather._fetch_hourly_forecast"
            ) as mock_forecast:
                mock_current.return_value = mock_current_weather_response
                mock_forecast.return_value = mock_forecast_response

                result = await fetch_weather("user123")

                # Verify default location was passed to fetchers
                mock_current.assert_called_once()
                args, kwargs = mock_current.call_args
                assert args[0] == 51.5074
                assert args[1] == -0.1278

    @pytest.mark.asyncio
    async def test_fetch_weather_partial_failure(
        self, mock_current_weather_response, mock_forecast_response
    ):
        """Test weather fetch gracefully handles partial failures."""
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
            with patch(
                "src.tools.weather._fetch_current_weather"
            ) as mock_current, patch(
                "src.tools.weather._fetch_hourly_forecast"
            ) as mock_forecast:
                # Current weather succeeds, forecast fails
                mock_current.return_value = mock_current_weather_response
                mock_forecast.side_effect = Exception("API Error")

                result = await fetch_weather("user123", 40.7128, -74.006)

                # Should still return valid result
                assert result["source"] == "weather"
                assert result["signals"]["current"]["temp"] == 18.5
                assert result["signals"]["forecast"]["forecast_count"] == 0

    @pytest.mark.asyncio
    async def test_fetch_weather_full_failure(self):
        """Test weather fetch handles complete failure."""
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
            with patch(
                "src.tools.weather._fetch_current_weather"
            ) as mock_current, patch(
                "src.tools.weather._fetch_hourly_forecast"
            ) as mock_forecast:
                # Both fail
                mock_current.side_effect = Exception("API Error")
                mock_forecast.side_effect = Exception("API Error")

                result = await fetch_weather("user123", 40.7128, -74.006)

                # Should still return valid result with empty signals
                assert result["source"] == "weather"
                assert result["signals"]["current"]["temp"] is None
                assert result["signals"]["forecast"]["forecast_count"] == 0
