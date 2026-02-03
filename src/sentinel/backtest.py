from __future__ import annotations

import argparse

from sentinel.core.backtest import BacktestResult, run_backtest
from sentinel.core.exchange import ExchangeConfig, create_exchange
from sentinel.core.io import write_json, write_text
from sentinel.core.ohlcv import OHLCVConfig, fetch_ohlcv_safe, split_ohlcv
from sentinel.core.setups import (
    BreakoutRetestConfig,
    PullbackConfig,
    detect_breakout_retest_long,
    detect_pullback_long,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SENTINEL backtest-lite (read-only).")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--pairs", default="BTC/USDT,ETH/USDT", help="comma-separated")
    p.add_argument("--timeframes", default="1h,4h", help="comma-separated")
    p.add_argument("--bars", type=int, default=800)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--out", default=None)
    return p.parse_args()


def _plans_to_series(symbol: str, closes: list[float], lows: list[float]) -> tuple[list[float], list[float], list[float]]:
    """
    Build per-index stop and tp1 by detecting setups at each index.
    For simplicity: evaluate setup using window up to i, and if setup exists, record stop/tp1.
    """
    stops: list[float] = []
    tp1s: list[float] = []
    entries: list[float] = []

    pb = PullbackConfig()
    br = BreakoutRetestConfig()

    for i in range(100, len(closes) - 1):
        c_win = closes[: i + 1]
        l_win = lows[: i + 1]

        plan = detect_pullback_long(c_win, l_win, symbol, pb)
        if plan is None:
            plan = detect_breakout_retest_long(c_win, l_win, symbol, br)

        if plan is None:
            continue

        entries.append(c_win[-1])
        stops.append(plan.stop)
        tp1s.append(plan.tp1)

    return entries, stops, tp1s


def format_text(results: list[BacktestResult]) -> str:
    lines: list[str] = []
    lines.append("SENTINEL backtest-lite (TP1=+1R, SL=-1R using candle closes)")
    lines.append("-" * 90)
    lines.append("SYMBOL".ljust(12) + "TF".ljust(6) + "TRADES".rjust(8) + "WIN%".rjust(8) + "AVG_R".rjust(10) + "PF".rjust(10) + "MDD_R".rjust(10))
    lines.append("-" * 90)
    for r in results:
        lines.append(
            f"{r.symbol.ljust(12)}{r.timeframe.ljust(6)}{r.trades:8d}{(r.win_rate*100):8.1f}{r.avg_r:10.3f}{r.profit_factor:10.2f}{r.max_drawdown_r:10.2f}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    ex = create_exchange(ExchangeConfig(exchange_id=args.exchange))

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    tfs = [t.strip() for t in args.timeframes.split(",") if t.strip()]

    results: list[BacktestResult] = []

    for sym in pairs:
        for tf in tfs:
            ohlcv = fetch_ohlcv_safe(ex, sym, OHLCVConfig(timeframe=tf, limit=args.bars))
            highs, lows, closes = split_ohlcv(ohlcv)
            if not closes or len(closes) < 200:
                continue

            entries, stops, tp1s = _plans_to_series(sym, closes, lows)
            if not entries:
                results.append(BacktestResult(sym, tf, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0))
                continue

            # For simulation we use entry closes list as "closes" series
            res = run_backtest(sym, tf, entries, stops, tp1s)
            results.append(res)

    if args.format == "json":
        payload = {"exchange": ex.id, "pairs": pairs, "timeframes": tfs, "results": results}
        if args.out:
            write_json(args.out, payload)
        else:
            print(payload)
    else:
        text = format_text(results)
        if args.out:
            write_text(args.out, text)
        else:
            print(text, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
