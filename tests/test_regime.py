from sentinel.core.regime import MarketRegime, classify_regime


def test_trend_regime() -> None:
    r = classify_regime(atr_pct=1.2, trend_strength=0.3)
    assert r == MarketRegime.TREND


def test_range_regime() -> None:
    r = classify_regime(atr_pct=0.1, trend_strength=0.05)
    assert r == MarketRegime.RANGE


def test_chaos_regime() -> None:
    r = classify_regime(atr_pct=12.0, trend_strength=0.4)
    assert r == MarketRegime.CHAOS
