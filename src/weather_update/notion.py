from __future__ import annotations

import csv
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError

from .models import WeatherReport

NOTION_VERSION = "2026-03-11"
MAX_RICH_TEXT_LENGTH = 1800
MAX_CHILDREN_PER_REQUEST = 100
MAX_TABLE_ROWS_PER_BLOCK = 100


@dataclass
class NotionClient:
    timeout_seconds: int = 30

    def create_page(self, token: str, parent_page_id: str, title: str, children: list[dict]) -> dict:
        payload = {
            "parent": {"type": "page_id", "page_id": _normalize_notion_id(parent_page_id)},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title},
                        }
                    ]
                }
            },
            "children": children[:MAX_CHILDREN_PER_REQUEST],
        }
        request = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status >= 400:
                    raise RuntimeError(f"Notion API failed: HTTP {response.status}: {body}")
                return json.loads(body)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            message = f"{exc}"
            if detail:
                message = f"{message}: {detail}"
            raise RuntimeError(message) from exc


def _text_block(block_type: str, text: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text},
                }
            ]
        },
    }


def _normalize_notion_id(raw_id: str) -> str:
    compact = raw_id.replace("-", "").strip()
    if len(compact) != 32:
        return raw_id.strip()
    return (
        f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-"
        f"{compact[16:20]}-{compact[20:]}"
    )


def _rich_text(content: str) -> list[dict]:
    return [
        {
            "type": "text",
            "text": {"content": content[:MAX_RICH_TEXT_LENGTH]},
        }
    ]


def _table_block(rows: list[list[str]]) -> dict | None:
    if not rows:
        return None
    width = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (width - len(row)) for row in rows]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [[item for item in _rich_text(cell)] for cell in row]
                    },
                }
                for row in normalized_rows
            ],
        },
    }


def _table_blocks(rows: list[list[str]]) -> list[dict]:
    if not rows:
        return []
    header = rows[0]
    data_rows = rows[1:]
    if not data_rows:
        block = _table_block([header])
        return [block] if block is not None else []

    blocks = []
    # Notion table block can contain at most 100 rows including header.
    chunk_size = MAX_TABLE_ROWS_PER_BLOCK - 1
    for start in range(0, len(data_rows), chunk_size):
        chunk_rows = [header, *data_rows[start : start + chunk_size]]
        block = _table_block(chunk_rows)
        if block is not None:
            blocks.append(block)
    return blocks


def build_notion_children(report: WeatherReport, markdown_path: Path, csv_path: Path, json_path: Path) -> list[dict]:
    children = [
        _text_block("heading_1", f"天気予報 {report.generated_at.isoformat()}"),
        _text_block("paragraph", f"対象件数: {len(report.records)}件"),
        _text_block("paragraph", f"警告件数: {len(report.warnings)}件"),
        _text_block("paragraph", "最低気温14℃以下は🔵、最高気温28℃以上は🔴で強調しています。"),
    ]

    csv_text = csv_path.read_text(encoding="utf-8-sig").strip()
    csv_rows = list(csv.reader(csv_text.splitlines()))
    table_blocks = _table_blocks(csv_rows)
    if table_blocks:
        children.extend(table_blocks)
    else:
        children.append(_text_block("paragraph", "CSV の内容を表として展開できませんでした。"))

    if report.warnings:
        children.append(_text_block("heading_2", "警告"))
        for warning in report.warnings[:20]:
            children.append(_text_block("bulleted_list_item", warning))

    return children[:MAX_CHILDREN_PER_REQUEST]


def extract_notion_page_url(page: dict) -> str | None:
    url = page.get("url") or page.get("public_url")
    if isinstance(url, str) and url:
        return url

    page_id = page.get("id")
    if isinstance(page_id, str) and page_id:
        compact = page_id.replace("-", "")
        return f"https://www.notion.so/{compact}"
    return None


def notify_notion(
    token: str,
    parent_page_id: str,
    report: WeatherReport,
    markdown_path: Path,
    csv_path: Path,
    json_path: Path,
    *,
    client: NotionClient | None = None,
) -> dict:
    notion_client = client or NotionClient()
    title = f"Weather Report {report.generated_at.isoformat()}"
    children = build_notion_children(report, markdown_path, csv_path, json_path)
    return notion_client.create_page(token, parent_page_id, title, children)
