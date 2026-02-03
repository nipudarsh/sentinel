from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradingPreset:
    key: str
    label: str
    timeframe: str
    bars: int
    refresh_seconds: int
    max_pairs: int


PRESETS: dict[str, TradingPreset] = {
    "scalping": TradingPreset(
        key="scalping",
        label="Scalping (fast)",
        timeframe="5m",
        bars=240,
        refresh_seconds=300,  # 5 minutes
        max_pairs=60,
    ),
    "intraday": TradingPreset(
        key="intraday",
        label="Intraday (day trading)",
        timeframe="15m",
        bars=240,
        refresh_seconds=600,  # 10 minutes
        max_pairs=60,
    ),
    "swing": TradingPreset(
        key="swing",
        label="Swing (4h)",
        timeframe="4h",
        bars=240,
        refresh_seconds=1800,  # 30 minutes
        max_pairs=50,
    ),
    "position": TradingPreset(
        key="position",
        label="Position (1d)",
        timeframe="1d",
        bars=365,
        refresh_seconds=3600,  # 60 minutes
        max_pairs=30,
    ),
}


def get_preset(key: str) -> TradingPreset:
    return PRESETS.get(key, PRESETS["swing"])
