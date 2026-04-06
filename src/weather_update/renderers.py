from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import Settings
from .models import WeatherReport


def _format_temperature(value: float | None, *, threshold: float, is_low: bool) -> str:
    if value is None:
        return "-"
    marker = ""
    if is_low and value <= threshold:
        marker = "🔵"
    if not is_low and value >= threshold:
        marker = "🔴"
    return f"{round(value)}°C{marker}"


def render_markdown(report: WeatherReport, settings: Settings) -> str:
    lines = [
        "# 天気予報出力",
        "",
        f"生成日: {report.generated_at.isoformat()}",
        f"最低気温{int(settings.low_temp_threshold)}℃以下は🔵、最高気温{int(settings.high_temp_threshold)}℃以上は🔴で強調しています。",
        "",
        "| 日付 | 都市名 | 予報天気 | 最低気温 | 最高気温 | 出典 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in report.records:
        lines.append(
            "| {date} | {city} | {weather} | {min_temp} | {max_temp} | {source} |".format(
                date=record.forecast_date.isoformat(),
                city=getattr(record, "city", "-"),
                weather=record.weather,
                min_temp=_format_temperature(
                    record.min_temp_c, threshold=settings.low_temp_threshold, is_low=True
                ),
                max_temp=_format_temperature(
                    record.max_temp_c, threshold=settings.high_temp_threshold, is_low=False
                ),
                source=record.source,
            )
        )
    if report.warnings:
        lines.extend(["", "## 警告", ""])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def write_csv(report: WeatherReport, settings: Settings, destination: Path) -> None:
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["日付", "都市名", "予報天気", "最低気温", "最高気温", "出典"])
        for record in report.records:
            writer.writerow(
                [
                    record.forecast_date.isoformat(),
                    getattr(record, "city", "-"),
                    record.weather,
                    _format_temperature(
                        record.min_temp_c, threshold=settings.low_temp_threshold, is_low=True
                    ),
                    _format_temperature(
                        record.max_temp_c, threshold=settings.high_temp_threshold, is_low=False
                    ),
                    record.source,
                ]
            )


def write_json(report: WeatherReport, destination: Path) -> None:
    payload = {
        "generated_at": report.generated_at.isoformat(),
        "records": [
            {
                "date": record.forecast_date.isoformat(),
                "city": getattr(record, "city", "-"),
                "weather": record.weather,
                "min_temp_c": record.min_temp_c,
                "max_temp_c": record.max_temp_c,
                "source": record.source,
            }
            for record in report.records
        ],
        "warnings": report.warnings,
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
