from __future__ import annotations

from dataclasses import dataclass

from sentinel.core.mathutils import ema
from sentinel.core.structure import near_level, recent_swing_low


@dataclass(frozen=True)
class PullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50

    # More realistic on 4h: pullbacks often drift for days
    pullback_lookback: int = 14

    # Wider tolerance to catch wick/close touches on liquid majors
    pullback_tolerance_pct: float = 2.2

    # Stop-loss uses recent structure
    swing_lookback: int = 30


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


def _ema_zone_touch(c: float, lo: float, e20: float, e50: float, tol_pct: float) -> bool:
    """
    Counts as a pullback if candle close OR wick is:
      - near EMA20, or near EMA50, OR
      - inside the EMA band (between EMA20 and EMA50) within tolerance.
    """
    # direct touches
    if near_level(c, e20, tol_pct) or near_level(c, e50, tol_pct) or near_level(lo, e20, tol_pct) or near_level(lo, e50, tol_pct):
        return True

    # band touch: wick enters the EMA20-EMA50 region
    top = max(e20, e50)
    bot = min(e20, e50)

    # expand band slightly by tolerance
    expand = top * (tol_pct / 100.0)
    top2 = top + expand
    bot2 = bot - expand

    return bot2 <= lo <= top2 or bot2 <= c <= top2


def _had_pullback_touch(
    closes: list[float],
    lows: list[float],
    e20: float,
    e50: float,
    tol_pct: float,
    lookback: int,
) -> bool:
    if len(closes) < 3:
        return False

    lb = min(lookback, len(closes) - 1)

    # Examine last lb candles excluding current candle
    for i in range(2, lb + 2):
        c = closes[-i]
        lo = lows[-i]
        if _ema_zone_touch(c, lo, e20, e50, tol_pct):
            return True

    return False


def detect_pullback_long(
    closes: list[float],
    lows: list[float],
    symbol: str,
    cfg: PullbackConfig,
) -> TradePlan | None:
    # Need enough candles for EMAs + structure
    if len(closes) < max(cfg.ema_fast, cfg.ema_slow) + 30:
        return None

    price = closes[-1]
    e20 = ema(closes, cfg.ema_fast)
    e50 = ema(closes, cfg.ema_slow)

    # Trend bias (LONG)
    if not (price > e50 and e20 > e50):
        return None

    # Pullback must touch EMA zone recently (multi-candle realistic)
    pulled_back = _had_pullback_touch(
        closes=closes,
        lows=lows,
        e20=e20,
        e50=e50,
        tol_pct=cfg.pullback_tolerance_pct,
        lookback=cfg.pullback_lookback,
    )
    if not pulled_back:
        return None

    # READY if currently above EMA20, else WATCH
    status = "READY" if price > e20 else "WATCH"

    # Trend sanity: require meaningful time above EMA20 recently
    recent = closes[-16:]
    if sum(1 for c in recent if c > e20) < 7:
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
            f"Pullback touched EMA band within last {cfg.pullback_lookback} candles. "
            "Manage at +1R / +2R; trail after +1R."
        ),
    )
