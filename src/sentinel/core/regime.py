from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketRegime(str, Enum):
    TREND = "trend"
    RANGE = "range"
    CHAOS = "chaos"


@dataclass(frozen=True)
class RegimeConfig:
    min_atr_pct: float = 0.3   # too low = dead market
    max_atr_pct: float = 8.0   # too high = chaos
    min_trend_strength: float = 0.15  # EMA separation proxy


def classify_regime(
    atr_pct: float,
    trend_strength: float,
    cfg: RegimeConfig = RegimeConfig(),
) -> MarketRegime:
    """
    Classify market regime using volatility + trend structure.
    atr_pct: ATR as % of price
    trend_strength: normalized EMA separation (0–1)
    """

    if atr_pct < cfg.min_atr_pct:
        return MarketRegime.RANGE

    if atr_pct > cfg.max_atr_pct:
        return MarketRegime.CHAOS

    if trend_strength >= cfg.min_trend_strength:
        return MarketRegime.TREND

    return MarketRegime.RANGE
