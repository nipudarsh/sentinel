from __future__ import annotations

import argparse

from sentinel.core.exchange import (
    ExchangeConfig,
    create_exchange,
    iter_usdt_symbols,
    load_markets_safe,
)



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SENTINEL: list USDT pairs (read-only).")
    p.add_argument("--exchange", default="binance", help="ccxt exchange id (default: binance)")
    p.add_argument("--limit", type=int, default=50, help="print first N pairs (default: 50)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    cfg = ExchangeConfig(exchange_id=args.exchange)
    ex = create_exchange(cfg)
    markets = load_markets_safe(ex)

    pairs = sorted(iter_usdt_symbols(markets))
    total = len(pairs)

    print(f"Exchange: {ex.id}")
    print(f"USDT pairs found: {total}")
    print("-" * 40)

    for sym in pairs[: max(args.limit, 0)]:
        print(sym)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
