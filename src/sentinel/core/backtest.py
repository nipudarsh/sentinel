from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    timeframe: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_r: float
    expectancy: float
    profit_factor: float
    max_drawdown_r: float


def _simulate_r_series(closes: list[float], stops: list[float], tp1s: list[float]) -> list[float]:
    """
    Very simple:
      - Entry at close[i]
      - Stop fixed
      - Take profit at tp1
      - Exit when close crosses stop or tp1
    Returns list of R outcomes.
    """
    out: list[float] = []
    for i in range(len(closes)):
        entry = closes[i]
        stop = stops[i]
        tp1 = tp1s[i]
        if entry <= 0 or stop <= 0 or stop >= entry:
            continue
        risk = entry - stop
        if risk <= 0:
            continue

        # walk forward
        r_out = 0.0
        hit = False
        for j in range(i + 1, min(i + 80, len(closes))):  # cap horizon
            c = closes[j]
            if c <= stop:
                r_out = -1.0
                hit = True
                break
            if c >= tp1:
                r_out = +1.0
                hit = True
                break
        if hit:
            out.append(r_out)
    return out


def summarize(symbol: str, timeframe: str, r_outcomes: list[float]) -> BacktestResult:
    trades = len(r_outcomes)
    if trades == 0:
        return BacktestResult(symbol, timeframe, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    wins = sum(1 for r in r_outcomes if r > 0)
    losses = sum(1 for r in r_outcomes if r < 0)
    win_rate = wins / trades

    avg_r = sum(r_outcomes) / trades
    expectancy = avg_r

    gross_win = sum(r for r in r_outcomes if r > 0)
    gross_loss = -sum(r for r in r_outcomes if r < 0)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    # max drawdown in R
    equity = 0.0
    peak = 0.0
    mdd = 0.0
    for r in r_outcomes:
        equity += r
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > mdd:
            mdd = dd

    return BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        trades=trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        avg_r=avg_r,
        expectancy=expectancy,
        profit_factor=profit_factor,
        max_drawdown_r=mdd,
    )


def run_backtest(symbol: str, timeframe: str, closes: list[float], stops: list[float], tp1s: list[float]) -> BacktestResult:
    r_outcomes = _simulate_r_series(closes, stops, tp1s)
    return summarize(symbol, timeframe, r_outcomes)
