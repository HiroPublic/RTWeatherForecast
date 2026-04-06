from datetime import date
from pathlib import Path

from weather_update.models import WeatherReport
from weather_update.service import EnrichedWeatherDataPoint
from weather_update.slack import build_slack_payload, notify_slack


class FakeSlackClient:
    def __init__(self) -> None:
        self.calls = []

    def post_json(self, url: str, payload: dict) -> None:
        self.calls.append((url, payload))


def test_build_slack_payload_contains_csv_content(tmp_path: Path) -> None:
    csv_path = tmp_path / "weather_report_2026-04-01.csv"
    csv_path.write_text(
        "日付,都市名,予報天気,最低気温,最高気温,出典\n"
        "2026-05-16,東京,晴れがちな平年,15°C,24°C,Open-Meteo / Climate\n"
        "2026-05-17,ニューヨーク,雨がちな平年,22°C,30°C,Open-Meteo / Climate\n"
        "2026-05-18,ニューヨーク,晴れがちな平年,20°C,32°C,Open-Meteo / Climate\n"
        "2026-05-19,ニューヨーク,雨がちな平年,21°C,30°C,Open-Meteo / Climate\n",
        encoding="utf-8",
    )
    report = WeatherReport(
        generated_at=date(2026, 4, 1),
        records=[
            EnrichedWeatherDataPoint(
                forecast_date=date(2026, 5, 16),
                city="東京",
                country="日本",
                weather="晴れがちな平年",
                min_temp_c=15.0,
                max_temp_c=24.0,
                source="Open-Meteo / Climate",
            )
        ],
        warnings=["2026-05-16 日本/東京: sample warning"],
    )

    payload = build_slack_payload(
        report,
        tmp_path / "weather_report_2026-04-01.md",
        csv_path,
        tmp_path / "weather_report_2026-04-01.json",
        notion_page_url="https://www.notion.so/example",
    )

    assert "天気予報を更新しました" in payload["text"]
    assert "対象件数: 1件" in payload["text"]
    assert "Notion: https://www.notion.so/example" in payload["text"]
    assert "CSV preview: 先頭3件" in payload["text"]
    assert "日付,都市名,予報天気,最低気温,最高気温,出典" in payload["text"]
    assert "2026-05-16,東京,晴れがちな平年,15°C,24°C,Open-Meteo / Climate" in payload["text"]
    assert "2026-05-18,ニューヨーク,晴れがちな平年,20°C,32°C,Open-Meteo / Climate" in payload["text"]
    assert "2026-05-19,ニューヨーク,雨がちな平年,21°C,30°C,Open-Meteo / Climate" not in payload["text"]
    assert "sample warning" in payload["text"]


def test_notify_slack_posts_payload() -> None:
    report = WeatherReport(generated_at=date(2026, 4, 1))
    client = FakeSlackClient()

    notify_slack(
        "https://hooks.slack.com/services/test",
        report,
        Path("a.md"),
        Path("a.csv"),
        Path("a.json"),
        client=client,
    )

    assert len(client.calls) == 1
    assert client.calls[0][0] == "https://hooks.slack.com/services/test"
