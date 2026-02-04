from sentinel.core.backtest import run_backtest


def test_backtest_smoke():
    closes = [100, 101, 102, 99, 103, 104, 98, 105]
    stops = [99, 99, 99]
    tp1s = [101, 101, 101]
    res = run_backtest("X/USDT", "1h", closes[:3], stops, tp1s)
    assert res.symbol == "X/USDT"
