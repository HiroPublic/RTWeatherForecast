from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import ItineraryStop, StayDate


DATE_FORMATS = ("%Y/%m/%d", "%Y-%m-%d")


def parse_date(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {raw}")


def load_itinerary(csv_path: Path) -> tuple[list[ItineraryStop], list[str]]:
    stops: list[ItineraryStop] = []
    warnings: list[str] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        for offset, row in enumerate(rows):
            index = offset + 2
            country = (row.get("国") or "").strip()
            city = (row.get("都市") or "").strip()
            if not country or not city:
                warnings.append(f"{index}行目: 国または都市が空のためスキップしました。")
                continue
            try:
                arrival_date = parse_date(row.get("到着日") or "")
                departure_date = parse_date(row.get("出発日") or "")
            except ValueError as exc:
                warnings.append(f"{index}行目: {exc} のためスキップしました。")
                continue
            if arrival_date and departure_date and arrival_date > departure_date:
                warnings.append(
                    f"{index}行目: 到着日 {arrival_date.isoformat()} が出発日 {departure_date.isoformat()} より後のためスキップしました。"
                )
                continue
            # Treat same-day intermediate rows as transit, but allow a trailing
            # same-day row so a final one-day stop can still be reported.
            if arrival_date and departure_date and arrival_date == departure_date and offset < len(rows) - 1:
                continue
            if not arrival_date and not departure_date:
                warnings.append(f"{index}行目: 到着日と出発日が空のためスキップしました。")
                continue
            stops.append(
                ItineraryStop(
                    country=country,
                    city=city,
                    arrival_date=arrival_date,
                    departure_date=departure_date,
                    row_number=index,
                )
            )
    return stops, warnings


def expand_itinerary(
    stops: list[ItineraryStop],
    *,
    today: date,
    compress_long_stays: bool = True,
) -> list[StayDate]:
    expanded: list[StayDate] = []
    for stop in stops:
        start_date = stop.arrival_date or stop.departure_date
        end_date = stop.departure_date or stop.arrival_date
        if start_date is None or end_date is None:
            continue
        if end_date < today:
            continue
        selected_dates = _selected_stay_dates(start_date, end_date, compress_long_stays=compress_long_stays)
        cursor = max(start_date, today)
        while cursor <= end_date:
            if cursor in selected_dates:
                expanded.append(
                    StayDate(
                        country=stop.country,
                        city=stop.city,
                        stay_date=cursor,
                        row_number=stop.row_number,
                    )
                )
            cursor += timedelta(days=1)
    return expanded


def _selected_stay_dates(start_date: date, end_date: date, *, compress_long_stays: bool) -> set[date]:
    stay_length = (end_date - start_date).days + 1
    if stay_length < 10 or not compress_long_stays:
        return {start_date + timedelta(days=offset) for offset in range(stay_length)}

    return {
        start_date,
        start_date + timedelta(days=1),
        end_date - timedelta(days=1),
        end_date,
    }
