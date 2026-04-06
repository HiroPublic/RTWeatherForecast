import os
from pathlib import Path

from weather_update.config import load_dotenv


def test_load_dotenv_sets_values_without_overwriting_existing_env(tmp_path: Path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        '# comment\n'
        'WEATHER_INPUT_CSV="from-dotenv.csv"\n'
        "export WEATHER_OUTPUT_DIR=dotenv-output\n"
        "WEATHER_GEOCODE_LANGUAGE=ja\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEATHER_OUTPUT_DIR", "already-set")

    load_dotenv(dotenv_path)

    assert os.environ["WEATHER_INPUT_CSV"] == "from-dotenv.csv"
    assert os.environ["WEATHER_OUTPUT_DIR"] == "already-set"
    assert os.environ["WEATHER_GEOCODE_LANGUAGE"] == "ja"
