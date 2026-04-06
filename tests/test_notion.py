from datetime import date
from pathlib import Path

from weather_update.models import WeatherReport
from weather_update.service import EnrichedWeatherDataPoint
from weather_update.notion import build_notion_children, extract_notion_page_url, notify_notion


class FakeNotionClient:
    def __init__(self) -> None:
        self.calls = []

    def create_page(self, token: str, parent_page_id: str, title: str, children: list[dict]) -> dict:
        self.calls.append((token, parent_page_id, title, children))
        return {"url": "https://www.notion.so/example"}


def test_build_notion_children_contains_csv_and_markdown(tmp_path: Path) -> None:
    markdown_path = tmp_path / "report.md"
    csv_path = tmp_path / "report.csv"
    json_path = tmp_path / "report.json"
    markdown_path.write_text("# title\nbody", encoding="utf-8")
    csv_path.write_text("日付,都市名\n2026-05-16,東京\n", encoding="utf-8")
    json_path.write_text("{}", encoding="utf-8")
    report = WeatherReport(
        generated_at=date(2026, 4, 1),
        records=[
            EnrichedWeatherDataPoint(
                forecast_date=date(2026, 5, 16),
                city="東京",
                country="日本",
                weather="晴れ",
                min_temp_c=15.0,
                max_temp_c=25.0,
                source="Open-Meteo",
            )
        ],
    )

    children = build_notion_children(report, markdown_path, csv_path, json_path)

    assert any(
        block["type"] == "paragraph"
        and block["paragraph"]["rich_text"][0]["text"]["content"] == "最低気温14℃以下は🔵、最高気温28℃以上は🔴で強調しています。"
        for block in children
    )
    assert any(block["type"] == "table" for block in children)
    assert not any(block["type"] == "code" for block in children)


def test_build_notion_children_splits_large_csv_into_multiple_tables(tmp_path: Path) -> None:
    markdown_path = tmp_path / "report.md"
    csv_path = tmp_path / "report.csv"
    json_path = tmp_path / "report.json"
    markdown_path.write_text("# title\nbody", encoding="utf-8")
    rows = ["日付,都市名,予報天気,最低気温,最高気温,出典"]
    for index in range(168):
        rows.append(f"2026-05-{index + 1:02d},都市{index},晴れ,10°C,20°C,Open-Meteo")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    json_path.write_text("{}", encoding="utf-8")
    report = WeatherReport(generated_at=date(2026, 4, 1))

    children = build_notion_children(report, markdown_path, csv_path, json_path)

    tables = [block for block in children if block["type"] == "table"]
    assert len(tables) == 2
    assert len(tables[0]["table"]["children"]) == 100
    assert len(tables[1]["table"]["children"]) == 70


def test_notify_notion_creates_child_page(tmp_path: Path) -> None:
    markdown_path = tmp_path / "report.md"
    csv_path = tmp_path / "report.csv"
    json_path = tmp_path / "report.json"
    markdown_path.write_text("content", encoding="utf-8")
    csv_path.write_text("h1,h2\nv1,v2\n", encoding="utf-8")
    json_path.write_text("{}", encoding="utf-8")
    report = WeatherReport(generated_at=date(2026, 4, 1))
    client = FakeNotionClient()

    response = notify_notion(
        "secret_test",
        "0123456789abcdef0123456789abcdef",
        report,
        markdown_path,
        csv_path,
        json_path,
        client=client,
    )

    assert response["url"] == "https://www.notion.so/example"
    assert len(client.calls) == 1
    assert client.calls[0][0] == "secret_test"
    assert client.calls[0][1] == "0123456789abcdef0123456789abcdef"
    assert client.calls[0][2] == "Weather Report 2026-04-01"


def test_extract_notion_page_url_falls_back_to_id() -> None:
    url = extract_notion_page_url({"id": "01234567-89ab-cdef-0123-456789abcdef"})

    assert url == "https://www.notion.so/0123456789abcdef0123456789abcdef"
