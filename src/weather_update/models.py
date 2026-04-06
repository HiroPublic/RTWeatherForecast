from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ItineraryStop:
    country: str
    city: str
    arrival_date: date | None
    departure_date: date | None
    row_number: int


@dataclass(frozen=True)
class StayDate:
    country: str
    city: str
    stay_date: date
    row_number: int


@dataclass(frozen=True)
class Location:
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True)
class WeatherDataPoint:
    forecast_date: date
    weather: str
    min_temp_c: float | None
    max_temp_c: float | None
    source: str


@dataclass
class WeatherReport:
    generated_at: date
    records: list[WeatherDataPoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
