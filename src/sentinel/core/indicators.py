from __future__ import annotations

import statistics


def atr_pct(highs: list[float], lows: list[float], closes: list[float]) -> float:
    """
    Very lightweight ATR percentage estimate.
    """
    if len(closes) < 2:
        return 0.0

    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    atr = statistics.mean(trs)
    price = closes[-1]
    return (atr / price) * 100 if price else 0.0


def trend_strength(ema_fast: float, ema_slow: float, price: float) -> float:
    """
    Normalized EMA separation as trend proxy.
    """
    if price == 0:
        return 0.0
    return abs(ema_fast - ema_slow) / price
