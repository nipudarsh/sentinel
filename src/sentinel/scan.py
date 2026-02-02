from __future__ import annotations

import argparse

from sentinel.core.exchange import (
    ExchangeConfig,
    create_exchange,
    iter_usdt_symbols,
    load_markets_safe,
)
from sentinel.core.filters import (
    PairFilterConfig,
    passes_market_filters,
    quote_volume_usdt_from_ticker,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SENTINEL: list USDT pairs (read-only).")
    p.add_argument("--exchange", default="binance", help="ccxt exchange id (default: binance)")
    p.add_argument("--limit", type=int, default=50, help="print first N pairs (default: 50)")

    p.add_argument("--quality", action="store_true", help="apply quality filters + volume ranking")
    p.add_argument(
        "--min-qv",
        type=float,
        default=5_000_000.0,
        help="min 24h quote volume in USDT for --quality (default: 5,000,000)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    ex = create_exchange(ExchangeConfig(exchange_id=args.exchange))
    markets = load_markets_safe(ex)

    pairs = list(iter_usdt_symbols(markets))

    print(f"Exchange: {ex.id}")
    print(f"USDT pairs found: {len(pairs)}")

    if not args.quality:
        print("-" * 40)
        for sym in sorted(pairs)[: max(args.limit, 0)]:
            print(sym)
        return 0

    # Quality mode
    cfg = PairFilterConfig(min_quote_volume_usdt=args.min_qv)

    # Fetch tickers once (public endpoint). This can be slow; we keep it simple.
    try:
        tickers = ex.fetch_tickers()
    except Exception as e:
        print(f"[WARN] fetch_tickers failed: {e}")
        tickers = {}

    scored: list[tuple[str, float]] = []
    rejected = 0

    for sym in pairs:
        market = markets.get(sym, {})
        if not passes_market_filters(sym, market, cfg):
            rejected += 1
            continue

        t = tickers.get(sym, {})
        qv = quote_volume_usdt_from_ticker(t)

        # If volume missing, we treat it as 0 and likely it will fall out of top list.
        scored.append((sym, qv or 0.0))

    scored.sort(key=lambda x: x[1], reverse=True)

    print(f"Rejected by rules: {rejected}")
    print(f"Quality candidates: {len(scored)}")
    print("-" * 40)

    shown = 0
    for sym, qv in scored:
        if qv < cfg.min_quote_volume_usdt:
            continue
        print(f"{sym}  |  quoteVolume(24h)≈ {qv:,.0f} USDT")
        shown += 1
        if shown >= max(args.limit, 0):
            break

    if shown == 0:
        print("[INFO] No pairs met the volume threshold. Lower --min-qv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
