from datetime import date
from pathlib import Path

from weather_update.itinerary import expand_itinerary, load_itinerary


def test_load_itinerary_skips_invalid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,,2026/05/01\n"
        "日本,大阪,2026/05/03,2026/05/02\n",
        encoding="utf-8",
    )
    stops, warnings = load_itinerary(csv_path)
    assert len(stops) == 1
    assert len(warnings) == 1


def test_load_itinerary_skips_transit_rows_with_same_arrival_and_departure(tmp_path: Path) -> None:
    csv_path = tmp_path / "itinerary.csv"
    csv_path.write_text(
        "国,都市,到着日,出発日\n"
        "日本,東京,2026/05/01,2026/05/01\n"
        "日本,大阪,2026/05/02,2026/05/03\n",
        encoding="utf-8",
    )

    stops, warnings = load_itinerary(csv_path)

    assert len(stops) == 1
    assert stops[0].city == "大阪"
    assert warnings == []


def test_expand_itinerary_creates_daily_rows() -> None:
    stops, _ = load_itinerary(Path("examples/itinerary.sample.csv"))
    days = expand_itinerary(stops[:1], today=date(2026, 5, 16))
    assert [item.stay_date.isoformat() for item in days] == ["2026-05-16"]


def test_expand_itinerary_limits_long_stays_to_first_two_and_last_two_days() -> None:
    stops, _ = load_itinerary(Path("examples/itinerary.sample.csv"))
    long_stop = stops[:1]
    long_stop[0] = long_stop[0].__class__(
        country=long_stop[0].country,
        city=long_stop[0].city,
        arrival_date=date(2026, 5, 16),
        departure_date=date(2026, 5, 27),
        row_number=long_stop[0].row_number,
    )

    days = expand_itinerary(long_stop, today=date(2026, 5, 16))

    assert [item.stay_date.isoformat() for item in days] == [
        "2026-05-16",
        "2026-05-17",
        "2026-05-26",
        "2026-05-27",
    ]


def test_expand_itinerary_skips_past_days_even_for_long_stays() -> None:
    stops, _ = load_itinerary(Path("examples/itinerary.sample.csv"))
    long_stop = stops[:1]
    long_stop[0] = long_stop[0].__class__(
        country=long_stop[0].country,
        city=long_stop[0].city,
        arrival_date=date(2026, 5, 16),
        departure_date=date(2026, 5, 27),
        row_number=long_stop[0].row_number,
    )

    days = expand_itinerary(long_stop, today=date(2026, 5, 20))

    assert [item.stay_date.isoformat() for item in days] == [
        "2026-05-26",
        "2026-05-27",
    ]


def test_expand_itinerary_does_not_compress_five_day_stays() -> None:
    stops, _ = load_itinerary(Path("examples/itinerary.sample.csv"))
    medium_stop = stops[:1]
    medium_stop[0] = medium_stop[0].__class__(
        country=medium_stop[0].country,
        city=medium_stop[0].city,
        arrival_date=date(2026, 5, 16),
        departure_date=date(2026, 5, 20),
        row_number=medium_stop[0].row_number,
    )

    days = expand_itinerary(medium_stop, today=date(2026, 5, 16))

    assert [item.stay_date.isoformat() for item in days] == [
        "2026-05-16",
        "2026-05-17",
        "2026-05-18",
        "2026-05-19",
        "2026-05-20",
    ]
