from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .itinerary import expand_itinerary, load_itinerary
from .models import WeatherDataPoint, WeatherReport
from .open_meteo import OpenMeteoClient
from .router import decide_source


@dataclass(frozen=True)
class EnrichedWeatherDataPoint(WeatherDataPoint):
    city: str
    country: str
    row_number: int = 0


class WeatherUpdateService:
    def __init__(self, client: OpenMeteoClient) -> None:
        self.client = client

    def build_report(
        self,
        input_csv,
        *,
        today: date,
        limit: int | None = None,
        progress_callback: Callable[[int, int, date, str, str], None] | None = None,
    ) -> WeatherReport:
        stops, warnings = load_itinerary(input_csv)
        stays = expand_itinerary(stops, today=today)
        if limit is not None:
            stays = stays[:limit]
        total_stays = len(stays)

        records: list[EnrichedWeatherDataPoint] = []
        for index, stay in enumerate(stays, start=1):
            if progress_callback and (index % 10 == 0 or index == total_stays):
                progress_callback(index, total_stays, stay.stay_date, stay.country, stay.city)
            try:
                decision = decide_source(stay, today=today)
                location = self.client.geocode(stay.city, stay.country)
                record = self._fetch_record(location, stay.stay_date, decision.provider_kind, decision.source_label, today=today)
                records.append(
                    EnrichedWeatherDataPoint(
                        forecast_date=record.forecast_date,
                        weather=record.weather,
                        min_temp_c=record.min_temp_c,
                        max_temp_c=record.max_temp_c,
                        source=record.source,
                        city=stay.city,
                        country=stay.country,
                        row_number=stay.row_number,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive path
                warnings.append(f"{stay.stay_date.isoformat()} {stay.country}/{stay.city}: {exc}")

        records.sort(key=lambda item: (item.forecast_date, item.row_number, item.city, item.country))
        return WeatherReport(generated_at=today, records=records, warnings=warnings)

    def _fetch_record(
        self,
        location,
        target_date: date,
        provider_kind: str,
        source_label: str,
        *,
        today: date,
    ) -> WeatherDataPoint:
        if provider_kind == "forecast":
            try:
                return self.client.fetch_forecast_day(location, target_date, source_label)
            except Exception as exc:
                if not self._is_forecast_range_error(exc):
                    raise
                return self.client.fetch_seasonal_day(
                    location,
                    target_date,
                    source_label,
                    today=today,
                )
        if provider_kind == "seasonal":
            return self.client.fetch_seasonal_day(
                location,
                target_date,
                source_label,
                today=today,
            )
        return self.client.fetch_climate_day(location, target_date, source_label)

    @staticmethod
    def _is_forecast_range_error(exc: Exception) -> bool:
        message = str(exc)
        return "Parameter 'start_date' is out of allowed range" in message
