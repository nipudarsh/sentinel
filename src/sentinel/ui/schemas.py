from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanRequest:
    exchange: str = "binance"
    preset: str = "swing"

    # optional overrides (if user changes from preset)
    timeframe: str | None = None
    bars: int | None = None
    refresh_seconds: int | None = None

    limit: int = 20
    max_pairs: int = 50

    quality: bool = True
    min_qv: float = 5_000_000.0

    regime: bool = True
    setups: bool = True
    brief: bool = True
    exclude_stables: bool = True

    risk_usdt: float = 1.0
    fee_buffer_pct: float = 0.10


@dataclass(frozen=True)
class ScanRow:
    symbol: str
    regime: str
    atr_pct: float
    trend_strength: float
    action: str
    note: str = ""


@dataclass(frozen=True)
class ScanResponse:
    exchange: str
    timeframe: str
    bars: int
    refresh_seconds: int
    rows: list[ScanRow]
    briefing: str
