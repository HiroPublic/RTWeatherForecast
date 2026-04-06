from datetime import date
from pathlib import Path

from weather_update.models import Location
from weather_update.open_meteo import OpenMeteoClient


class StubHttpClient:
    def __init__(self, response: dict):
        self.response = response
        self.urls = []

    def get_json(self, url: str) -> dict:
        self.urls.append(url)
        return self.response


def test_fetch_climate_day_builds_weather_label_from_precipitation(tmp_path: Path) -> None:
    http_client = StubHttpClient(
        {
            "daily": {
                "temperature_2m_min_MRI_AGCM3_2_S": [18.0],
                "temperature_2m_min_EC_Earth3P_HR": [20.0],
                "temperature_2m_max_MRI_AGCM3_2_S": [27.0],
                "temperature_2m_max_EC_Earth3P_HR": [29.0],
                "precipitation_sum_MRI_AGCM3_2_S": [14.0],
                "precipitation_sum_EC_Earth3P_HR": [10.0],
                "snowfall_sum_MRI_AGCM3_2_S": [0.0],
                "snowfall_sum_EC_Earth3P_HR": [0.0],
                "cloud_cover_mean_MRI_AGCM3_2_S": [90.0],
                "cloud_cover_mean_EC_Earth3P_HR": [88.0],
            }
        }
    )
    client = OpenMeteoClient(cache_dir=tmp_path, http_client=http_client)
    location = Location("リスボン", "ポルトガル", 38.72, -9.14, "Europe/Lisbon")

    record = client.fetch_climate_day(location, date(2026, 5, 26), "Open-Meteo")

    assert "precipitation_sum" in http_client.urls[0]
    assert "cloud_cover_mean" in http_client.urls[0]
    assert record.weather == "雨が多い平年"
    assert record.min_temp_c == 19.0
    assert record.max_temp_c == 28.0
