from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from urllib.error import HTTPError
from urllib.error import URLError
from pathlib import Path

import certifi

from .models import Location, WeatherDataPoint


WEATHER_CODE_LABELS = {
    0: "晴れ",
    1: "晴れ",
    2: "晴れ時々くもり",
    3: "くもり",
    45: "霧",
    48: "霧",
    51: "小雨",
    53: "雨",
    55: "強い雨",
    56: "みぞれ",
    57: "みぞれ",
    61: "小雨",
    63: "雨",
    65: "大雨",
    66: "みぞれ",
    67: "みぞれ",
    71: "雪",
    73: "雪",
    75: "大雪",
    77: "雪",
    80: "にわか雨",
    81: "雨",
    82: "強い雨",
    85: "雪",
    86: "大雪",
    95: "雷雨",
    96: "雷雨",
    99: "激しい雷雨",
}

COUNTRY_MATCH_ALIASES = {
    "日本": {"日本", "Japan", "JP"},
    "USA": {"USA", "United States", "United States of America", "US"},
    "アメリカ": {"USA", "United States", "United States of America", "US"},
    "ポルトガル": {"ポルトガル", "Portugal", "PT"},
    "スペイン": {"スペイン", "Spain", "ES"},
    "ギリシャ": {"ギリシャ", "Greece", "GR"},
    "イタリア": {"イタリア", "Italy", "IT"},
    "トルコ": {"トルコ", "Turkey", "TR"},
    "南アフリカ": {"南アフリカ", "South Africa", "ZA"},
    "ナミビア": {"ナミビア", "Namibia", "NA"},
    "ジンバブエ": {"ジンバブエ", "Zimbabwe", "ZW"},
    "ボツワナ": {"ボツワナ", "Botswana", "BW"},
    "ペルー": {"ペルー", "Peru", "PE"},
    "ニュージーランド": {"ニュージーランド", "New Zealand", "NZ"},
}

CITY_SEARCH_ALIASES = {
    ("イタリア", "ベネチア"): "Venice",
    ("日本", "大阪"): "Osaka",
    ("トルコ", "カッパドキア"): "Cappadocia",
    ("南アフリカ", "クルーガー国立公園（Hoedspruit）"): "Hoedspruit",
    ("ナミビア", "ナミブ砂漠（Windhoek, Sossusvlei）"): "Sossusvlei",
    ("ジンバブエ", "ビクトリア滝"): "Victoria Falls",
    ("ボツワナ", "チョベ国立公園（Kasane）"): "Kasane",
    ("南アフリカ", "ケープワインランド（Stellenbosch+Franschhoek）"): "Stellenbosch",
    ("ペルー", "ウルバンバ"): "Urubamba",
    ("ペルー", "マチュピチュ"): "Machu Picchu",
    ("ペルー", "アマゾン"): "Puerto Maldonado",
    ("ニュージーランド", "テカポ湖"): "Lake Tekapo",
}


@dataclass
class JsonHttpClient:
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5
    ssl_context: ssl.SSLContext | None = None

    def __post_init__(self) -> None:
        if self.ssl_context is None:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    def get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": "weather-update-system/0.1"})
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                    context=self.ssl_context,
                ) as response:
                    return json.load(response)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace").strip()
                message = f"{exc}"
                if detail:
                    message = f"{message}: {detail}"
                raise RuntimeError(message) from exc
            except (TimeoutError, socket.timeout, ssl.SSLError, URLError) as exc:
                if not self._is_retryable_network_error(exc):
                    raise
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)
        if last_error is not None:
            raise RuntimeError(
                f"Open-Meteo request failed after {self.max_retries} attempts: {last_error}"
            ) from last_error
        raise RuntimeError("Open-Meteo request failed without a captured error.")

    @staticmethod
    def _is_retryable_network_error(exc: Exception) -> bool:
        if isinstance(exc, URLError):
            reason = exc.reason
            return isinstance(reason, (TimeoutError, socket.timeout, ssl.SSLError))
        return isinstance(exc, (TimeoutError, socket.timeout, ssl.SSLError))


class OpenMeteoClient:
    def __init__(self, *, cache_dir: Path, language: str = "ja", http_client: JsonHttpClient | None = None) -> None:
        self.cache_dir = cache_dir
        self.language = language
        self.http_client = http_client or JsonHttpClient()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._geocode_cache_path = self.cache_dir / "geocode_cache.json"
        self._geocode_cache = self._load_cache(self._geocode_cache_path)

    @staticmethod
    def _load_cache(path: Path) -> dict[str, dict]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _save_cache(path: Path, data: dict[str, dict]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def geocode(self, city: str, country: str) -> Location:
        cache_key = f"{country}:{city}"
        if cache_key in self._geocode_cache:
            payload = self._geocode_cache[cache_key]
            return Location(**payload)

        results = self._geocode_results(city, country)
        if not results:
            alias = CITY_SEARCH_ALIASES.get((country, city))
            if alias:
                results = self._geocode_results(alias, country)
        if not results:
            raise LookupError(f"都市を解決できませんでした: {country} / {city}")

        country_aliases = COUNTRY_MATCH_ALIASES.get(country, {country})
        best = next(
            (
                item
                for item in results
                if (item.get("country") or "") in country_aliases or (item.get("country_code") or "") in country_aliases
            ),
            results[0],
        )
        location = Location(
            city=city,
            country=country,
            latitude=float(best["latitude"]),
            longitude=float(best["longitude"]),
            timezone=best.get("timezone") or "auto",
        )
        self._geocode_cache[cache_key] = {
            "city": location.city,
            "country": location.country,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
        }
        self._save_cache(self._geocode_cache_path, self._geocode_cache)
        return location

    def _geocode_results(self, city: str, country: str) -> list[dict]:
        params = urllib.parse.urlencode(
            {"name": city, "count": 10, "language": self.language, "format": "json"}
        )
        url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
        payload = self.http_client.get_json(url)
        return payload.get("results") or []

    def fetch_forecast_day(self, location: Location, target_date: date, source_label: str) -> WeatherDataPoint:
        params = urllib.parse.urlencode(
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "daily": "weather_code,temperature_2m_min,temperature_2m_max",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        payload = self.http_client.get_json(url)
        daily = payload["daily"]
        return WeatherDataPoint(
            forecast_date=target_date,
            weather=WEATHER_CODE_LABELS.get(daily["weather_code"][0], "不明"),
            min_temp_c=daily["temperature_2m_min"][0],
            max_temp_c=daily["temperature_2m_max"][0],
            source=source_label,
        )

    def fetch_seasonal_day(
        self,
        location: Location,
        target_date: date,
        source_label: str,
        *,
        today: date,
    ) -> WeatherDataPoint:
        forecast_days = (target_date - today).days + 1
        if forecast_days <= 0:
            raise ValueError(f"target_date must be on or after today: {target_date.isoformat()} < {today.isoformat()}")
        params = urllib.parse.urlencode(
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
                "forecast_days": forecast_days,
                "daily": "weather_code,temperature_2m_min,temperature_2m_max",
            }
        )
        url = f"https://seasonal-api.open-meteo.com/v1/forecast?{params}"
        payload = self.http_client.get_json(url)
        daily = payload.get("daily") or {}
        times = daily.get("time") or []
        if target_date.isoformat() not in times:
            return self.fetch_climate_day(location, target_date, source_label)

        target_index = times.index(target_date.isoformat())
        weather_code = self._value_at(daily.get("weather_code"), target_index)
        min_temp = self._value_at(daily.get("temperature_2m_min"), target_index)
        max_temp = self._value_at(daily.get("temperature_2m_max"), target_index)

        if weather_code is None or min_temp is None or max_temp is None:
            return self.fetch_climate_day(location, target_date, source_label)

        return WeatherDataPoint(
            forecast_date=target_date,
            weather=WEATHER_CODE_LABELS.get(weather_code, "平年値ベース"),
            min_temp_c=min_temp,
            max_temp_c=max_temp,
            source=source_label,
        )

    def fetch_climate_day(self, location: Location, target_date: date, source_label: str) -> WeatherDataPoint:
        params = urllib.parse.urlencode(
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "models": "MRI_AGCM3_2_S,EC_Earth3P_HR,NICAM16_8S",
                "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,snowfall_sum,cloud_cover_mean",
            }
        )
        url = f"https://climate-api.open-meteo.com/v1/climate?{params}"
        payload = self.http_client.get_json(url)
        daily = payload.get("daily") or {}
        min_temp = self._daily_value(daily, "temperature_2m_min", 0)
        max_temp = self._daily_value(daily, "temperature_2m_max", 0)
        precipitation_sum = self._daily_value(daily, "precipitation_sum", 0)
        snowfall_sum = self._daily_value(daily, "snowfall_sum", 0)
        cloud_cover_mean = self._daily_value(daily, "cloud_cover_mean", 0)
        if min_temp is None or max_temp is None:
            raise KeyError(f"Climate API response is missing temperature values: {sorted(daily.keys())}")
        return WeatherDataPoint(
            forecast_date=target_date,
            weather=self._climate_weather_label(
                precipitation_sum=precipitation_sum,
                snowfall_sum=snowfall_sum,
                cloud_cover_mean=cloud_cover_mean,
            ),
            min_temp_c=min_temp,
            max_temp_c=max_temp,
            source=f"{source_label} / Climate",
        )

    @staticmethod
    def _value_at(values: list | None, index: int):
        if not values or index >= len(values):
            return None
        value = values[index]
        if value in ("", None):
            return None
        return value

    @classmethod
    def _daily_value(cls, daily: dict, base_key: str, index: int) -> float | None:
        direct_value = cls._value_at(daily.get(base_key), index)
        if direct_value is not None:
            return direct_value

        prefixed_values = []
        prefix = f"{base_key}_"
        for key, series in daily.items():
            if not key.startswith(prefix):
                continue
            value = cls._value_at(series, index)
            if value is not None:
                prefixed_values.append(float(value))
        if prefixed_values:
            return sum(prefixed_values) / len(prefixed_values)
        return None

    @staticmethod
    def _climate_weather_label(
        *,
        precipitation_sum: float | None,
        snowfall_sum: float | None,
        cloud_cover_mean: float | None,
    ) -> str:
        if snowfall_sum is not None and snowfall_sum >= 1.0:
            return "雪が多い平年"
        if precipitation_sum is not None:
            if precipitation_sum >= 12.0:
                return "雨が多い平年"
            if precipitation_sum >= 3.0:
                return "雨がちな平年"
        if cloud_cover_mean is not None:
            if cloud_cover_mean <= 25.0:
                return "晴れがちな平年"
            if cloud_cover_mean <= 60.0:
                return "晴れ時々くもりの平年"
            if cloud_cover_mean <= 85.0:
                return "くもりがちな平年"
            return "くもりや雨がちな平年"
        return "平年値ベース"
