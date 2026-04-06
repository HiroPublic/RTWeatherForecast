from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import StayDate


@dataclass(frozen=True)
class SourceDecision:
    provider_kind: str
    source_label: str


ASIA_COUNTRIES = {"日本", "中国", "韓国", "台湾", "タイ", "ベトナム", "インド", "インドネシア", "シンガポール", "マレーシア"}
EUROPE_COUNTRIES = {
    "ポルトガル",
    "スペイン",
    "イタリア",
    "フランス",
    "ドイツ",
    "ベルギー",
    "ギリシャ",
    "イギリス",
    "オランダ",
    "スイス",
}
NORTH_AMERICA_COUNTRIES = {"USA", "アメリカ", "カナダ", "メキシコ"}
MIDDLE_EAST_AFRICA_COUNTRIES = {"エジプト", "モロッコ", "ケニア", "南アフリカ", "UAE", "アラブ首長国連邦", "イスラエル", "トルコ"}
SOUTH_AMERICA_COUNTRIES = {"ペルー", "チリ", "ボリビア", "アルゼンチン", "ブラジル", "コロンビア", "エクアドル"}


def _regional_label(country: str) -> str:
    if country in ASIA_COUNTRIES:
        return "JMA/ECMWF"
    if country in EUROPE_COUNTRIES or country in NORTH_AMERICA_COUNTRIES:
        return "ECMWF/DWD/NOAA"
    if country in MIDDLE_EAST_AFRICA_COUNTRIES:
        return "Seasonal"
    if country in SOUTH_AMERICA_COUNTRIES:
        return "Seasonal"
    return "Global"


def decide_source(stay: StayDate, *, today: date) -> SourceDecision:
    horizon_days = (stay.stay_date - today).days
    if horizon_days <= 16:
        provider_kind = "forecast"
    elif horizon_days <= 215:
        provider_kind = "seasonal"
    else:
        provider_kind = "climate"
    return SourceDecision(provider_kind=provider_kind, source_label=_regional_label(stay.country))
