from __future__ import annotations


def ema(values: list[float], period: int) -> float:
    """
    Simple EMA (exponential moving average).
    Returns the last EMA value.
    """
    if period <= 0:
        raise ValueError("period must be > 0")
    if not values:
        return 0.0
    if len(values) < period:
        # fall back to simple average of what's available
        return sum(values) / len(values)

    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = (v * k) + (e * (1 - k))
    return e
