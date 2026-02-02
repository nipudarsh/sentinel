from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import ccxt


@dataclass(frozen=True)
class ExchangeConfig:
    exchange_id: str = "binance"
    timeout_ms: int = 20000
    enable_rate_limit: bool = True


class ExchangeError(RuntimeError):
    pass


def create_exchange(cfg: ExchangeConfig) -> ccxt.Exchange:
    """
    Create a CCXT exchange instance configured for safe, public-data usage.
    No API keys required.
    """
    try:
        klass = getattr(ccxt, cfg.exchange_id)
    except AttributeError as e:
        raise ExchangeError(f"Unsupported exchange_id: {cfg.exchange_id}") from e

    ex = klass(
        {
            "enableRateLimit": cfg.enable_rate_limit,
            "timeout": cfg.timeout_ms,
        }
    )

    # Optional: some exchanges require explicit options setup
    # Keep conservative defaults; public endpoints only.
    return ex


def load_markets_safe(ex: ccxt.Exchange) -> dict:
    """
    Load markets with clear error wrapping.
    """
    try:
        return ex.load_markets()
    except Exception as e:
        raise ExchangeError(f"Failed to load markets from {ex.id}: {e}") from e


def iter_usdt_symbols(markets: dict) -> Iterable[str]:
    """
    Yield symbols that trade against USDT (spot or futures depending on exchange defaults).
    """
    for sym, _info in markets.items():
        # sym usually like "BTC/USDT"
        if isinstance(sym, str) and sym.endswith("/USDT"):
            yield sym
