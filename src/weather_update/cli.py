from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .config import Settings, load_dotenv
from .open_meteo import OpenMeteoClient
from .notion import extract_notion_page_url, notify_notion
from .renderers import render_markdown, write_csv, write_json
from .service import WeatherUpdateService
from .slack import notify_slack


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="旅程ベースの天気予報自動更新システム")
    parser.add_argument("--input", type=Path, help="旅程CSVのパス")
    parser.add_argument("--output-dir", type=Path, help="出力先ディレクトリ")
    parser.add_argument("--cache-dir", type=Path, help="キャッシュディレクトリ")
    parser.add_argument("--today", type=date.fromisoformat, help="テスト用基準日 (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="先頭から処理する滞在日数の上限")
    return parser.parse_args()


def main() -> int:
    root_dir = Path(__file__).resolve().parents[2]
    load_dotenv(root_dir / ".env")
    args = _parse_args()
    settings = Settings.from_env(root_dir)
    if args.input:
        settings = Settings(
            input_csv=args.input,
            output_dir=settings.output_dir,
            cache_dir=settings.cache_dir,
            slack_webhook_url=settings.slack_webhook_url,
            notion_token=settings.notion_token,
            notion_parent_page_id=settings.notion_parent_page_id,
            low_temp_threshold=settings.low_temp_threshold,
            high_temp_threshold=settings.high_temp_threshold,
            geocode_language=settings.geocode_language,
        )
    if args.output_dir:
        settings = Settings(
            input_csv=settings.input_csv,
            output_dir=args.output_dir,
            cache_dir=settings.cache_dir,
            slack_webhook_url=settings.slack_webhook_url,
            notion_token=settings.notion_token,
            notion_parent_page_id=settings.notion_parent_page_id,
            low_temp_threshold=settings.low_temp_threshold,
            high_temp_threshold=settings.high_temp_threshold,
            geocode_language=settings.geocode_language,
        )
    if args.cache_dir:
        settings = Settings(
            input_csv=settings.input_csv,
            output_dir=settings.output_dir,
            cache_dir=args.cache_dir,
            slack_webhook_url=settings.slack_webhook_url,
            notion_token=settings.notion_token,
            notion_parent_page_id=settings.notion_parent_page_id,
            low_temp_threshold=settings.low_temp_threshold,
            high_temp_threshold=settings.high_temp_threshold,
            geocode_language=settings.geocode_language,
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    today = args.today or date.today()
    client = OpenMeteoClient(cache_dir=settings.cache_dir, language=settings.geocode_language)
    service = WeatherUpdateService(client)
    report = service.build_report(
        settings.input_csv,
        today=today,
        limit=args.limit,
        progress_callback=lambda done, total, stay_date, country, city: print(
            f"Progress: {done}/{total} ({stay_date.isoformat()} {country}/{city})"
        ),
    )

    base_name = f"weather_report_{today.isoformat()}"
    markdown_path = settings.output_dir / f"{base_name}.md"
    csv_path = settings.output_dir / f"{base_name}.csv"
    json_path = settings.output_dir / f"{base_name}.json"

    markdown_path.write_text(render_markdown(report, settings), encoding="utf-8")
    write_csv(report, settings, csv_path)
    write_json(report, json_path)

    notion_page_url = None

    if settings.notion_token or settings.notion_parent_page_id:
        if not settings.notion_token or not settings.notion_parent_page_id:
            raise ValueError("Both WEATHER_NOTION_TOKEN and WEATHER_NOTION_PARENT_PAGE_ID are required for Notion.")
        notion_page = notify_notion(
            settings.notion_token,
            settings.notion_parent_page_id,
            report,
            markdown_path,
            csv_path,
            json_path,
        )
        notion_page_url = extract_notion_page_url(notion_page)
        print(f"Notion page created: {notion_page_url or '(no url returned)'}")

    if settings.slack_webhook_url:
        notify_slack(
            settings.slack_webhook_url,
            report,
            markdown_path,
            csv_path,
            json_path,
            notion_page_url=notion_page_url,
        )
        print("Slack notification sent.")

    print(f"Generated: {markdown_path}")
    print(f"Generated: {csv_path}")
    print(f"Generated: {json_path}")
    if report.warnings:
        print(f"Warnings: {len(report.warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
