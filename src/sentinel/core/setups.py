from __future__ import annotations

from dataclasses import dataclass

from sentinel.core.mathutils import ema
from sentinel.core.structure import near_level, recent_swing_low


@dataclass(frozen=True)
class PullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50

    # How close price/wick must come to EMA zone to count as a pullback
    pullback_tolerance_pct: float = 1.5

    # Look back N candles to find a pullback touch (more realistic than only prev candle)
    pullback_lookback: int = 6

    # Stop-loss uses recent structure
    swing_lookback: int = 24


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str  # "long"
    status: str  # "WATCH" or "READY"
    entry_trigger: str
    stop: float
    tp1: float
    tp2: float
    notes: str


def _had_pullback_touch(
    closes: list[float],
    lows: list[float],
    e20: float,
    e50: float,
    tolerance_pct: float,
    lookback: int,
) -> bool:
    if len(closes) < 3:
        return False
    lb = min(lookback, len(closes) - 1)
    # Examine last lb candles excluding the current candle
    for i in range(2, lb + 2):
        c = closes[-i]
        lo = lows[-i]
        if (
            near_level(c, e20, tolerance_pct)
            or near_level(c, e50, tolerance_pct)
            or near_level(lo, e20, tolerance_pct)
            or near_level(lo, e50, tolerance_pct)
        ):
            return True
    return False


def detect_pullback_long(
    closes: list[float],
    lows: list[float],
    symbol: str,
    cfg: PullbackConfig,
) -> TradePlan | None:
    # Need enough candles for EMAs + structure
    if len(closes) < max(cfg.ema_fast, cfg.ema_slow) + 20:
        return None

    price = closes[-1]
    e20 = ema(closes, cfg.ema_fast)
    e50 = ema(closes, cfg.ema_slow)

    # Trend bias (LONG)
    if not (price > e50 and e20 > e50):
        return None

    # Pullback must have touched EMA zone recently (multi-candle realistic)
    pulled_back = _had_pullback_touch(
        closes=closes,
        lows=lows,
        e20=e20,
        e50=e50,
        tolerance_pct=cfg.pullback_tolerance_pct,
        lookback=cfg.pullback_lookback,
    )
    if not pulled_back:
        return None

    # READY if currently above EMA20, otherwise WATCH
    status = "READY" if price > e20 else "WATCH"

    # Sanity: trend must have existed recently (avoid chop)
    recent_closes = closes[-12:]
    if sum(1 for c in recent_closes if c > e20) < 6:
        return None

    # Stop-loss: recent swing low
    sl = recent_swing_low(lows, lookback=cfg.swing_lookback)
    if sl <= 0 or sl >= price:
        return None

    risk = price - sl
    if risk <= 0:
        return None

    tp1 = price + risk * 1.0
    tp2 = price + risk * 2.0

    trigger = (
        f"Enter on confirmation: close above EMA{cfg.ema_fast} (4h)."
        if status == "WATCH"
        else f"Confirmation met (close > EMA{cfg.ema_fast}). Enter only if next 4h candle holds above EMA{cfg.ema_fast}."
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
            f"Pullback touched EMA zone within last {cfg.pullback_lookback} candles. "
            "Manage at +1R / +2R; trail after +1R."
        ),
    )
