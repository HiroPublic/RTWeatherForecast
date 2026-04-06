from __future__ import annotations

import csv
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .models import WeatherReport

MAX_SLACK_TEXT_LENGTH = 3500


@dataclass
class SlackWebhookClient:
    timeout_seconds: int = 30

    def post_json(self, url: str, payload: dict) -> None:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
            if response.status >= 400:
                raise RuntimeError(f"Slack webhook failed: HTTP {response.status}: {body}")
            if body and body != "ok":
                raise RuntimeError(f"Slack webhook returned unexpected response: {body}")


def build_slack_payload(
    report: WeatherReport,
    markdown_path: Path,
    csv_path: Path,
    json_path: Path,
    *,
    notion_page_url: str | None = None,
) -> dict:
    csv_text = "CSV preview is unavailable."
    if csv_path.exists():
        csv_rows = list(csv.reader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
        csv_text = "\n".join(",".join(row) for row in csv_rows[:4])
    if len(csv_text) > MAX_SLACK_TEXT_LENGTH:
        csv_text = csv_text[: MAX_SLACK_TEXT_LENGTH - len("\n... (truncated)")] + "\n... (truncated)"

    lines = [
        f"*天気予報を更新しました* ({report.generated_at.isoformat()})",
        f"対象件数: {len(report.records)}件",
        f"警告件数: {len(report.warnings)}件",
        "CSV preview: 先頭3件",
    ]
    lines.extend(
        [
            "",
            "```",
            csv_text,
            "```",
        ]
    )
    if report.warnings:
        lines.append("")
        lines.append("*警告抜粋*")
        for warning in report.warnings[:3]:
            lines.append(f"- {warning}")
    if notion_page_url:
        lines.append("")
        lines.append(f"Notion: {notion_page_url}")

    return {"text": "\n".join(lines)}


def notify_slack(
    webhook_url: str,
    report: WeatherReport,
    markdown_path: Path,
    csv_path: Path,
    json_path: Path,
    *,
    notion_page_url: str | None = None,
    client: SlackWebhookClient | None = None,
) -> None:
    slack_client = client or SlackWebhookClient()
    slack_client.post_json(
        webhook_url,
        build_slack_payload(
            report,
            markdown_path,
            csv_path,
            json_path,
            notion_page_url=notion_page_url,
        ),
    )
