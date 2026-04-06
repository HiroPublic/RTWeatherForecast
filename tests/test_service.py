from datetime import date
from pathlib import Path

from weather_update.models import Location, WeatherDataPoint
from weather_update.service import WeatherUpdateService


class FakeClient:
    def geocode(self, city: str, country: str) -> Location:
        return Location(city=city, country=country, latitude=35.0, longitude=139.0, timezone="Asia/Tokyo")

    def fetch_forecast_day(self, location: Location, target_date: date, source_label: str) -> WeatherDataPoint:
        return WeatherDataPoint(target_date, "晴れ", 13.0, 27.0, source_label)

    def fetch_seasonal_day(
        self,
        location: Location,
        target_date: date,
        source_label: str,
        *,
        today: date,
    ) -> WeatherDataPoint:
        return WeatherDataPoint(target_date, "晴れ", 18.0, 31.0, source_label)

    def fetch_climate_day(self, location: Location, target_date: date, source_label: str) -> WeatherDataPoint:
        return WeatherDataPoint(target_date, "平年値ベース", 20.0, 29.0, source_label)


def test_service_builds_records(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,2026/04/03,2026/04/04\n"
        "スペイン,マドリード,2026/05/10,2026/05/10\n",
        encoding="utf-8",
    )
    service = WeatherUpdateService(FakeClient())
    report = service.build_report(csv_path, today=date(2026, 4, 1))
    assert len(report.records) == 3
    assert report.records[0].city == "東京"


def test_service_keeps_same_day_order_from_itinerary_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,2026/04/01,2026/04/03\n"
        "日本,大阪,2026/04/03,2026/04/05\n",
        encoding="utf-8",
    )
    service = WeatherUpdateService(FakeClient())

    report = service.build_report(csv_path, today=date(2026, 4, 1))

    same_day_records = [record for record in report.records if record.forecast_date == date(2026, 4, 3)]
    assert [record.city for record in same_day_records] == ["東京", "大阪"]


def test_service_reports_progress_every_ten_items_and_last_item(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,2026/04/01,2026/04/12\n",
        encoding="utf-8",
    )
    service = WeatherUpdateService(FakeClient())
    progress_events = []

    report = service.build_report(
        csv_path,
        today=date(2026, 4, 1),
        progress_callback=lambda done, total, stay_date, country, city: progress_events.append(
            (done, total, stay_date.isoformat(), country, city)
        ),
    )

    assert len(report.records) == 4
    assert progress_events == [
        (4, 4, "2026-04-12", "日本", "東京"),
    ]


def test_service_can_limit_processed_stays(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,2026/04/01,2026/04/10\n",
        encoding="utf-8",
    )
    service = WeatherUpdateService(FakeClient())

    report = service.build_report(csv_path, today=date(2026, 4, 1), limit=5)

    assert len(report.records) == 4
    assert [record.forecast_date.isoformat() for record in report.records] == [
        "2026-04-01",
        "2026-04-02",
        "2026-04-09",
        "2026-04-10",
    ]
