from __future__ import annotations


def recent_swing_low(lows: list[float], lookback: int = 20) -> float:
    if not lows:
        return 0.0
    window = lows[-lookback:] if len(lows) >= lookback else lows
    return min(window)


def near_level(price: float, level: float, tolerance_pct: float) -> bool:
    if level == 0:
        return False
    return abs(price - level) / level * 100 <= tolerance_pct
