#!/bin/zsh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_CSV="${WEATHER_INPUT_CSV:-$ROOT_DIR/examples/itinerary.sample.csv}"
OUTPUT_DIR="${WEATHER_OUTPUT_DIR:-$ROOT_DIR/output}"

cd "$ROOT_DIR"
PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 -m weather_update.cli \
  --input "$INPUT_CSV" \
  --output-dir "$OUTPUT_DIR"
