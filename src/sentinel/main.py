from __future__ import annotations

from sentinel import __version__


def main() -> int:
    print(f"SENTINEL v{__version__} — boot OK")
    print("")
    print("Commands:")
    print("  python -m sentinel.scan --exclude-stables --quality --regime --setups --brief --timeframe 4h")
    print("  python -m sentinel.scan --format json --out reports/scan.json --exclude-stables --quality --regime --setups")
    print("  python -m sentinel.backtest --pairs BTC/USDT,ETH/USDT --timeframes 1h,4h --bars 800")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
