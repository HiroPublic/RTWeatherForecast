from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    input_csv: Path
    output_dir: Path
    cache_dir: Path
    slack_webhook_url: str | None = None
    notion_token: str | None = None
    notion_parent_page_id: str | None = None
    low_temp_threshold: float = 14.0
    high_temp_threshold: float = 28.0
    geocode_language: str = "ja"

    @classmethod
    def from_env(cls, root_dir: Path) -> "Settings":
        input_csv = Path(
            os.getenv("WEATHER_INPUT_CSV", str(root_dir / "examples" / "itinerary.sample.csv"))
        )
        output_dir = Path(os.getenv("WEATHER_OUTPUT_DIR", str(root_dir / "output")))
        cache_dir = Path(os.getenv("WEATHER_CACHE_DIR", str(root_dir / ".cache")))
        slack_webhook_url = os.getenv("WEATHER_SLACK_WEBHOOK_URL") or None
        notion_token = os.getenv("WEATHER_NOTION_TOKEN") or None
        notion_parent_page_id = os.getenv("WEATHER_NOTION_PARENT_PAGE_ID") or None
        low_threshold = float(os.getenv("WEATHER_LOW_TEMP_THRESHOLD", "14"))
        high_threshold = float(os.getenv("WEATHER_HIGH_TEMP_THRESHOLD", "28"))
        language = os.getenv("WEATHER_GEOCODE_LANGUAGE", "ja")
        return cls(
            input_csv=input_csv,
            output_dir=output_dir,
            cache_dir=cache_dir,
            slack_webhook_url=slack_webhook_url,
            notion_token=notion_token,
            notion_parent_page_id=notion_parent_page_id,
            low_temp_threshold=low_threshold,
            high_temp_threshold=high_threshold,
            geocode_language=language,
        )
