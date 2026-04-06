from datetime import date
from pathlib import Path

from weather_update.config import Settings
from weather_update.renderers import render_markdown, write_json
from weather_update.service import EnrichedWeatherDataPoint
from weather_update.models import WeatherReport


def test_render_markdown_highlights_thresholds(tmp_path: Path) -> None:
    settings = Settings(
        input_csv=tmp_path / "input.csv",
        output_dir=tmp_path,
        cache_dir=tmp_path / ".cache",
    )
    report = WeatherReport(
        generated_at=date(2026, 4, 1),
        records=[
            EnrichedWeatherDataPoint(
                forecast_date=date(2026, 5, 1),
                city="東京",
                country="日本",
                row_number=2,
                weather="晴れ",
                min_temp_c=12,
                max_temp_c=30,
                source="Open-Meteo",
            )
        ],
    )
    markdown = render_markdown(report, settings)
    assert "12°C🔵" in markdown
    assert "30°C🔴" in markdown


def test_write_json_contains_city(tmp_path: Path) -> None:
    report = WeatherReport(
        generated_at=date(2026, 4, 1),
        records=[
            EnrichedWeatherDataPoint(
                forecast_date=date(2026, 5, 1),
                city="東京",
                country="日本",
                row_number=2,
                weather="晴れ",
                min_temp_c=12,
                max_temp_c=25,
                source="Open-Meteo",
            )
        ],
    )
    destination = tmp_path / "report.json"
    write_json(report, destination)
    assert '"city": "東京"' in destination.read_text(encoding="utf-8")
