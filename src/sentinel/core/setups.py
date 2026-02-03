from __future__ import annotations

from dataclasses import dataclass

from sentinel.core.mathutils import ema
from sentinel.core.structure import near_level, recent_swing_low


@dataclass(frozen=True)
class PullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    pullback_tolerance_pct: float = 1.2  # relaxed, realistic
    swing_lookback: int = 20

@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str  # "long"
    status: str     # "WATCH" or "READY"
    entry_trigger: str
    stop: float
    tp1: float
    tp2: float
    notes: str

@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str  # "long"
    entry_trigger: str
    stop: float
    tp1: float
    tp2: float
    notes: str


def detect_pullback_long(
    closes: list[float],
    lows: list[float],
    symbol: str,
    cfg: PullbackConfig,
) -> TradePlan | None:
    # Need enough candles
    if len(closes) < max(cfg.ema_fast, cfg.ema_slow) + 10:
        return None

    price = closes[-1]
    e20 = ema(closes, cfg.ema_fast)
    e50 = ema(closes, cfg.ema_slow)

    # Trend bias (LONG)
    if not (price > e50 and e20 > e50):
        return None

    prev_close = closes[-2]
    prev_low = lows[-2]

    # Pullback via close OR wick near EMA20 / EMA50
    pulled_back = (
        near_level(prev_close, e20, cfg.pullback_tolerance_pct)
        or near_level(prev_close, e50, cfg.pullback_tolerance_pct)
        or near_level(prev_low, e20, cfg.pullback_tolerance_pct)
        or near_level(prev_low, e50, cfg.pullback_tolerance_pct)
    )

        if not pulled_back:
        return None

    status = "READY" if price > e20 else "WATCH"

    # Sanity: was price above EMA20 recently (avoid chop)
    recent_closes = closes[-10:]
    if not any(c > e20 for c in recent_closes):
        return None

    sl = recent_swing_low(lows, lookback=cfg.swing_lookback)
    if sl <= 0 or sl >= price:
        return None

    risk = price - sl
    if risk <= 0:
        return None

    tp1 = price + risk * 1.0
    tp2 = price + risk * 2.0

    trigger = (
        f"Enter on confirmation: close above EMA{cfg.ema_fast}."
        if status == "WATCH"
        else f"Confirmation met (close > EMA{cfg.ema_fast}). Enter only if next candle holds above EMA{cfg.ema_fast}."
    )

    return TradePlan(
        symbol=symbol,
        direction="long",
        status=status,
        entry_trigger=trigger,
        stop=sl,
        tp1=tp1,
        tp2=tp2,
        notes=(
            f"Trend continuation: EMA{cfg.ema_fast} > EMA{cfg.ema_slow}. "
            "Pullback via wick/close near EMA. Manage at +1R / +2R."
        ),
    )

        
    
