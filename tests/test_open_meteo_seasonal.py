from datetime import date
from pathlib import Path

from weather_update.models import Location
from weather_update.open_meteo import OpenMeteoClient


class StubHttpClient:
    def __init__(self, response: dict | list[dict]):
        if isinstance(response, list):
            self.responses = response
        else:
            self.responses = [response]
        self.urls = []

    def get_json(self, url: str) -> dict:
        self.urls.append(url)
        return self.responses.pop(0)


def test_fetch_seasonal_day_uses_forecast_days_and_picks_matching_date(tmp_path: Path) -> None:
    http_client = StubHttpClient(
        {
            "daily": {
                "time": ["2026-05-16", "2026-05-17", "2026-05-18"],
                "weather_code": [3, 0, 1],
                "temperature_2m_min": [10.0, 11.0, 12.0],
                "temperature_2m_max": [20.0, 21.0, 22.0],
            }
        }
    )
    client = OpenMeteoClient(cache_dir=tmp_path, http_client=http_client)
    location = Location("東京", "日本", 35.0, 139.0, "Asia/Tokyo")

    record = client.fetch_seasonal_day(
        location,
        date(2026, 5, 17),
        "Open-Meteo Seasonal",
        today=date(2026, 5, 16),
    )

    assert "forecast_days=2" in http_client.urls[0]
    assert record.forecast_date == date(2026, 5, 17)
    assert record.weather == "晴れ"
    assert record.min_temp_c == 11.0
    assert record.max_temp_c == 21.0


def test_fetch_seasonal_day_falls_back_to_climate_when_values_are_missing(tmp_path: Path) -> None:
    http_client = StubHttpClient(
        [
            {
                "daily": {
                    "time": ["2026-05-16", "2026-05-17"],
                    "weather_code": [None, None],
                    "temperature_2m_min": [None, None],
                    "temperature_2m_max": [None, None],
                }
            },
            {
                "daily": {
                    "temperature_2m_min": [15.0],
                    "temperature_2m_max": [24.0],
                    "precipitation_sum": [4.0],
                    "snowfall_sum": [0.0],
                    "cloud_cover_mean": [70.0],
                }
            },
        ]
    )
    client = OpenMeteoClient(cache_dir=tmp_path, http_client=http_client)
    location = Location("東京", "日本", 35.0, 139.0, "Asia/Tokyo")
    record = client.fetch_seasonal_day(
        location,
        date(2026, 5, 17),
        "Open-Meteo Seasonal",
        today=date(2026, 5, 16),
    )

    assert record.weather == "雨がちな平年"
    assert record.min_temp_c == 15.0
    assert record.max_temp_c == 24.0
    assert record.source == "Open-Meteo Seasonal / Climate"
