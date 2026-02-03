from __future__ import annotations

from dataclasses import dataclass

import ccxt

from sentinel.core.exchange import ExchangeError


@dataclass(frozen=True)
class OHLCVConfig:
    timeframe: str = "15m"
    limit: int = 120  # enough for EMAs + ATR estimate


def fetch_ohlcv_safe(ex: ccxt.Exchange, symbol: str, cfg: OHLCVConfig) -> list[list[float]]:
    """
    Fetch OHLCV with error wrapping.
    Returns list of [timestamp, open, high, low, close, volume]
    """
    try:
        return ex.fetch_ohlcv(symbol, timeframe=cfg.timeframe, limit=cfg.limit)
    except Exception as e:
        raise ExchangeError(f"fetch_ohlcv failed for {symbol} on {ex.id}: {e}") from e


def split_ohlcv(ohlcv: list[list[float]]) -> tuple[list[float], list[float], list[float]]:
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    for row in ohlcv:
        # [ts, o, h, l, c, v]
        highs.append(float(row[2]))
        lows.append(float(row[3]))
        closes.append(float(row[4]))
    return highs, lows, closes
