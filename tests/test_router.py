from datetime import date

from weather_update.models import StayDate
from weather_update.router import decide_source


def test_decide_source_uses_forecast_through_14_days() -> None:
    stay = StayDate(country="トルコ", city="イスタンブール", stay_date=date(2026, 6, 1), row_number=2)

    decision = decide_source(stay, today=date(2026, 5, 18))

    assert decision.provider_kind == "forecast"


def test_decide_source_switches_to_seasonal_after_14_days() -> None:
    stay = StayDate(country="トルコ", city="イスタンブール", stay_date=date(2026, 6, 2), row_number=2)

    decision = decide_source(stay, today=date(2026, 5, 18))

    assert decision.provider_kind == "seasonal"
