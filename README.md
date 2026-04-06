# RTWeatherForecast

旅程 CSV を入力として、滞在日ごとの天気予報をまとめたレポートを生成する Python ツールです。Open-Meteo の短期予報、季節予報、気候データを日付レンジに応じて切り替え、Markdown、CSV、JSON を同時に出力します。

## Features

- 旅程 CSV の読込と日付検証
- 滞在日単位への展開
- 都市名と国名によるジオコーディング
- 予報レンジに応じた Open-Meteo API の自動切替
- 出典ラベルの付与
- Markdown、CSV、JSON の同時出力
- ローカルキャッシュ
- Slack 通知
- Notion へのページ保存
- ユニットテスト

## Requirements

- Python 3.11 以上
- Open-Meteo API へ接続できるネットワーク環境

## Quick Start

```bash
python3 -m pip install -e .
cp .env.sample .env
PYTHONPATH=src python3 -m weather_update.cli \
  --input ./examples/itinerary.sample.csv \
  --output-dir ./output
```

最初の数件だけ確認したい場合:

```bash
PYTHONPATH=src python3 -m weather_update.cli \
  --input ./examples/itinerary.sample.csv \
  --output-dir ./output \
  --today 2026-04-01 \
  --limit 5
```

## Configuration

`.env` を使う場合は、`.env.sample` をコピーして必要な値を埋めてください。すでにシェルで設定済みの環境変数がある場合は、そちらが優先されます。

```dotenv
WEATHER_INPUT_CSV="./examples/itinerary.sample.csv"
WEATHER_OUTPUT_DIR="./output"
WEATHER_CACHE_DIR="./.cache"
WEATHER_SLACK_WEBHOOK_URL=""
WEATHER_NOTION_TOKEN=""
WEATHER_NOTION_PARENT_PAGE_ID=""
WEATHER_LOW_TEMP_THRESHOLD="14"
WEATHER_HIGH_TEMP_THRESHOLD="28"
WEATHER_GEOCODE_LANGUAGE="ja"
```

Slack と Notion は任意です。使わない場合は空のままにしてください。

## Output

生成物:

- `output/weather_report_YYYY-MM-DD.md`
- `output/weather_report_YYYY-MM-DD.csv`
- `output/weather_report_YYYY-MM-DD.json`

出力列:

- `日付`
- `都市名`
- `予報天気`
- `最低気温`
- `最高気温`
- `出典`

しきい値の強調:

- `最低気温 <= 14°C` の場合は `🔵`
- `最高気温 >= 28°C` の場合は `🔴`

## Slack Integration

`WEATHER_SLACK_WEBHOOK_URL` が設定されている場合、実行完了後に Slack へサマリを送信します。

設定手順:

1. Slack でアプリを作成する
2. Incoming Webhooks を有効化する
3. `Add New Webhook to Workspace` から通知先チャンネルを選ぶ
4. 発行された Webhook URL を `WEATHER_SLACK_WEBHOOK_URL` に設定する

参考:

- [Sending messages using incoming webhooks](https://api.slack.com/messaging/webhooks)

## Notion Integration

`WEATHER_NOTION_TOKEN` と `WEATHER_NOTION_PARENT_PAGE_ID` の両方が設定されている場合、実行完了後に Notion の親ページ配下へ子ページを作成し、CSV と Markdown を保存します。

設定手順:

1. Notion の `My integrations` を開く
2. `New integration` から Internal integration を作成する
3. `Insert content` を有効にする
4. Internal Integration Token をコピーする
5. 保存先ページに Integration を接続する
6. 対象ページの URL からページ ID を取得する
7. `WEATHER_NOTION_TOKEN` と `WEATHER_NOTION_PARENT_PAGE_ID` を設定する

参考:

- [Authorization](https://developers.notion.com/docs/authorization)
- [Create a page](https://developers.notion.com/reference/post-page)
- [Working with page content](https://developers.notion.com/docs/working-with-page-content)

## GitHub Actions Configuration

GitHub Actions からレポート生成や通知を行う場合は、次の値を登録してください。

Repository secrets:

- `WEATHER_SLACK_WEBHOOK_URL`
  Slack Incoming Webhook URL。Slack 通知を使う場合だけ必要です。
- `WEATHER_NOTION_TOKEN`
  Notion Integration Token。Notion 連携を使う場合に必要です。
- `WEATHER_NOTION_PARENT_PAGE_ID`
  保存先の Notion ページ ID。`WEATHER_NOTION_TOKEN` とセットで必要です。

Repository variables:

- `WEATHER_INPUT_CSV`
  Actions 上で使う旅程 CSV のパス。既定値は `./examples/itinerary.sample.csv` です。
- `WEATHER_OUTPUT_DIR`
  出力先ディレクトリ。既定値は `./output` です。
- `WEATHER_CACHE_DIR`
  キャッシュディレクトリ。既定値は `./.cache` です。
- `WEATHER_LOW_TEMP_THRESHOLD`
  低温ハイライト閾値。既定値は `14` です。
- `WEATHER_HIGH_TEMP_THRESHOLD`
  高温ハイライト閾値。既定値は `28` です。
- `WEATHER_GEOCODE_LANGUAGE`
  ジオコーディング言語。既定値は `ja` です。

Secrets と Variables の登録場所:

1. GitHub リポジトリの `Settings`
2. `Secrets and variables`
3. `Actions`

Actions には `CI` に加えて `Generate Weather Report` workflow があり、上の Secrets と Variables を読んで実行します。

## Automation

日次実行の例:

```bash
./scripts/run_daily_update.sh
```

`cron` 例:

```bash
0 7 * * * cd /path/to/RTWeatherForecast && ./scripts/run_daily_update.sh
```

## Development

テスト実行:

```bash
pytest
```

依存関係を変更した場合は、再度次を実行します。

```bash
python3 -m pip install -e .
```

## Notes

- Open-Meteo の短期予報は最大 16 日先まで取得できます
- 季節予報は約 7 か月先まで取得できます
- それより先の日付は気候データで補完します
- シークレット値は `.env` に置き、Git に含めない運用を想定しています
