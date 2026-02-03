from __future__ import annotations

import argparse

from sentinel.core.exchange import (
    ExchangeConfig,
    ExchangeError,
    create_exchange,
    iter_usdt_symbols,
    load_markets_safe,
)
from sentinel.core.filters import (
    PairFilterConfig,
    passes_market_filters,
    quote_volume_usdt_from_ticker,
)
from sentinel.core.indicators import atr_pct, trend_strength
from sentinel.core.mathutils import ema
from sentinel.core.ohlcv import OHLCVConfig, fetch_ohlcv_safe, split_ohlcv
from sentinel.core.regime import MarketRegime, classify_regime


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SENTINEL: scan USDT pairs (read-only).")
    p.add_argument("--exchange", default="binance", help="ccxt exchange id (default: binance)")
    p.add_argument("--limit", type=int, default=30, help="how many pairs to print (default: 30)")

    p.add_argument("--quality", action="store_true", help="apply quality filters + volume ranking")
    p.add_argument("--min-qv", type=float, default=5_000_000.0, help="min 24h quote volume for quality mode")

    p.add_argument("--regime", action="store_true", help="compute TREND/RANGE/CHAOS for each pair (slower)")
    p.add_argument("--timeframe", default="15m", help="ohlcv timeframe for regime (default: 15m)")
    p.add_argument("--bars", type=int, default=120, help="ohlcv bars to fetch (default: 120)")
    p.add_argument("--max-pairs", type=int, default=60, help="max pairs to analyze for regime (default: 60)")

    return p.parse_args()


def rank_quality_pairs(ex, markets: dict, pairs: list[str], min_qv: float) -> list[str]:
    cfg = PairFilterConfig(min_quote_volume_usdt=min_qv)

    try:
        tickers = ex.fetch_tickers()
    except Exception as e:
        print(f"[WARN] fetch_tickers failed: {e}")
        tickers = {}

    scored: list[tuple[str, float]] = []
    for sym in pairs:
        market = markets.get(sym, {})
        if not passes_market_filters(sym, market, cfg):
            continue
        qv = quote_volume_usdt_from_ticker(tickers.get(sym, {})) or 0.0
        scored.append((sym, qv))

    scored.sort(key=lambda x: x[1], reverse=True)

    # keep only those above threshold first; if none, keep top anyway
    above = [s for (s, qv) in scored if qv >= min_qv]
    if above:
        return above
    return [s for (s, _qv) in scored]


def compute_regime_for_symbol(ex, symbol: str, timeframe: str, bars: int) -> tuple[MarketRegime, float, float]:
    ohlcv = fetch_ohlcv_safe(ex, symbol, OHLCVConfig(timeframe=timeframe, limit=bars))
    highs, lows, closes = split_ohlcv(ohlcv)
    if not closes:
        return MarketRegime.RANGE, 0.0, 0.0

    a = atr_pct(highs, lows, closes)
    price = closes[-1]
    ema_fast = ema(closes, 20)
    ema_slow = ema(closes, 50)
    ts = trend_strength(ema_fast, ema_slow, price)
    r = classify_regime(a, ts)
    return r, a, ts


def main() -> int:
    args = parse_args()

    ex = create_exchange(ExchangeConfig(exchange_id=args.exchange))
    markets = load_markets_safe(ex)
    pairs = list(iter_usdt_symbols(markets))

    print(f"Exchange: {ex.id}")
    print(f"USDT pairs found: {len(pairs)}")

    # Choose pair list
    if args.quality:
        pairs = rank_quality_pairs(ex, markets, pairs, args.min_qv)

    # If not regime mode, just print list
    if not args.regime:
        print("-" * 40)
        for sym in sorted(pairs)[: max(args.limit, 0)]:
            print(sym)
        return 0

    # Regime mode (slower): analyze top N pairs only
    pairs = pairs[: max(args.max_pairs, 0)]
    print(f"Regime analysis on: {len(pairs)} pairs | tf={args.timeframe} bars={args.bars}")
    print("-" * 70)
    print("SYMBOL".ljust(16), "REGIME".ljust(8), "ATR%".rjust(7), "TREND".rjust(7), "ACTION")
    print("-" * 70)

    shown = 0
    for sym in pairs:
        try:
            r, a, ts = compute_regime_for_symbol(ex, sym, args.timeframe, args.bars)
        except ExchangeError as e:
            print(f"{sym.ljust(16)} ERROR    {'-':>7} {'-':>7}  skip ({e})")
            continue

        action = "trade-allowed" if r == MarketRegime.TREND else ("limited" if r == MarketRegime.RANGE else "NO TRADE")
        print(f"{sym.ljust(16)} {r.value.ljust(8)} {a:7.2f} {ts:7.3f}  {action}")

        shown += 1
        if shown >= max(args.limit, 0):
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
