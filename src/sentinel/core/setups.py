from __future__ import annotations

from dataclasses import dataclass

from sentinel.core.mathutils import ema
from sentinel.core.structure import near_level, recent_swing_low


@dataclass(frozen=True)
class PullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    pullback_lookback: int = 14
    pullback_tolerance_pct: float = 2.2
    swing_lookback: int = 30


@dataclass(frozen=True)
class BreakoutRetestConfig:
    breakout_lookback: int = 40
    retest_lookback: int = 10
    retest_tolerance_pct: float = 1.0
    swing_lookback: int = 30


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str  # "long"
    setup: str  # "PULLBACK" or "BREAKOUT_RETEST"
    status: str  # "WATCH" or "READY"
    entry_ref: float
    entry_trigger: str
    stop: float
    tp1: float
    tp2: float
    notes: str


def _ema_zone_touch(c: float, lo: float, e20: float, e50: float, tol_pct: float) -> bool:
    if (
        near_level(c, e20, tol_pct)
        or near_level(c, e50, tol_pct)
        or near_level(lo, e20, tol_pct)
        or near_level(lo, e50, tol_pct)
    ):
        return True

    top = max(e20, e50)
    bot = min(e20, e50)
    expand = top * (tol_pct / 100.0)
    top2 = top + expand
    bot2 = bot - expand
    return bot2 <= lo <= top2 or bot2 <= c <= top2


def _had_pullback_touch(closes: list[float], lows: list[float], e20: float, e50: float, tol_pct: float, lookback: int) -> bool:
    if len(closes) < 3:
        return False
    lb = min(lookback, len(closes) - 1)
    for i in range(2, lb + 2):
        c = closes[-i]
        lo = lows[-i]
        if _ema_zone_touch(c, lo, e20, e50, tol_pct):
            return True
    return False


def detect_pullback_long(closes: list[float], lows: list[float], symbol: str, cfg: PullbackConfig) -> TradePlan | None:
    if len(closes) < max(cfg.ema_fast, cfg.ema_slow) + 30:
        return None

    price = closes[-1]
    e20 = ema(closes, cfg.ema_fast)
    e50 = ema(closes, cfg.ema_slow)

    if not (price > e50 and e20 > e50):
        return None

    if not _had_pullback_touch(closes, lows, e20, e50, cfg.pullback_tolerance_pct, cfg.pullback_lookback):
        return None

    status = "READY" if price > e20 else "WATCH"

    sl = recent_swing_low(lows, lookback=cfg.swing_lookback)
    if sl <= 0 or sl >= price:
        return None

    risk = price - sl
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
        setup="PULLBACK",
        status=status,
        entry_ref=price,
        entry_trigger=trigger,
        stop=sl,
        tp1=tp1,
        tp2=tp2,
        notes=f"Pullback touched EMA band within last {cfg.pullback_lookback} candles.",
    )


def _recent_swing_high(closes: list[float], lookback: int) -> float:
    if not closes:
        return 0.0
    window = closes[-lookback:] if len(closes) >= lookback else closes
    return max(window)


def detect_breakout_retest_long(closes: list[float], lows: list[float], symbol: str, cfg: BreakoutRetestConfig) -> TradePlan | None:
    if len(closes) < cfg.breakout_lookback + 10:
        return None

    price = closes[-1]
    level = _recent_swing_high(closes[:-1], cfg.breakout_lookback)
    if level <= 0:
        return None

    broke = any(c > level for c in closes[-(cfg.retest_lookback + 5) :])
    if not broke:
        return None

    lb = min(cfg.retest_lookback, len(lows) - 1)
    retested = any(near_level(lows[-i], level, cfg.retest_tolerance_pct) for i in range(2, lb + 2))
    if not retested:
        return None

    status = "READY" if price > level else "WATCH"

    sl = recent_swing_low(lows, lookback=cfg.swing_lookback)
    if sl <= 0 or sl >= price:
        return None

    risk = price - sl
    tp1 = price + risk * 1.0
    tp2 = price + risk * 2.0

    trigger = (
        f"Enter on confirmation: close back above breakout level ({level:.6f})."
        if status == "WATCH"
        else f"Reclaim confirmed (close > {level:.6f}). Enter only if next candle holds above it."
    )

    return TradePlan(
        symbol=symbol,
        direction="long",
        setup="BREAKOUT_RETEST",
        status=status,
        entry_ref=price,
        entry_trigger=trigger,
        stop=sl,
        tp1=tp1,
        tp2=tp2,
        notes=f"Breakout+retest: level≈{level:.6f}, retest in last {cfg.retest_lookback} candles.",
    )
