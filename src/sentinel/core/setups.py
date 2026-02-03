from __future__ import annotations

from dataclasses import dataclass

from sentinel.core.mathutils import ema
from sentinel.core.structure import near_level, recent_swing_low


@dataclass(frozen=True)
class PullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    pullback_tolerance_pct: float = 1.2  # “near EMA” threshold
    swing_lookback: int = 20


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str  # "long"
    entry_trigger: str
    stop: float
    tp1: float
    tp2: float
    notes: str


def detect_pullback_long(closes: list[float], lows: list[float], symbol: str, cfg: PullbackConfig) -> TradePlan | None:
    if len(closes) < max(cfg.ema_fast, cfg.ema_slow) + 5:
        return None

    price = closes[-1]
    e20 = ema(closes, cfg.ema_fast)
    e50 = ema(closes, cfg.ema_slow)

    # Trend bias for LONG: price above slow EMA and fast EMA above slow EMA
    if not (price > e50 and e20 > e50):
        return None

    # Pullback condition: recent close was near EMA20 or EMA50
    prev_close = closes[-2]
prev_low = lows[-2]

# Pullback if either the previous close OR wick (low) came near EMA20/EMA50
pulled_back = (
    near_level(prev_close, e20, cfg.pullback_tolerance_pct)
    or near_level(prev_close, e50, cfg.pullback_tolerance_pct)
    or near_level(prev_low, e20, cfg.pullback_tolerance_pct)
    or near_level(prev_low, e50, cfg.pullback_tolerance_pct)
)

    if not pulled_back:
        return None

    # Confirmation trigger: close back above EMA20
    if not (price > e20):
        return None
    # Sanity: ensure we were above EMA20 during the recent trend (avoid chop)
recent = closes[-10:]
if not any(c > e20 for c in recent):
    return None


    sl = recent_swing_low(lows, lookback=cfg.swing_lookback)
    if sl <= 0 or sl >= price:
        return None

    # R-based targets using stop distance
    risk = price - sl
    tp1 = price + risk * 1.0
    tp2 = price + risk * 2.0

    return TradePlan(
        symbol=symbol,
        direction="long",
        entry_trigger=f"Enter only if next candle holds above EMA{cfg.ema_fast} (current close > EMA{cfg.ema_fast}).",
        stop=sl,
        tp1=tp1,
        tp2=tp2,
        notes=f"Trend OK (EMA{cfg.ema_fast} > EMA{cfg.ema_slow}). Pullback detected near EMA. Manage at +1R / +2R.",
    )
