from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PairFilterConfig:
    # Exclude leveraged tokens and other synthetic tickers by default
    exclude_leveraged_tokens: bool = True

    # Basic liquidity filter: keep only markets with >= this quote volume (USDT)
    min_quote_volume_usdt: float = 5_000_000.0

    # Keep only active markets (when exchange provides this field)
    require_active: bool = True


_LEVERAGED_SUFFIXES = ("UP/USDT", "DOWN/USDT", "BULL/USDT", "BEAR/USDT")


def is_leveraged_token(symbol: str) -> bool:
    s = symbol.upper()
    return any(s.endswith(suf) for suf in _LEVERAGED_SUFFIXES)


def market_is_active(market: dict) -> bool:
    # CCXT market often has "active": True/False/None
    active = market.get("active", None)
    return bool(active) if active is not None else True


def passes_market_filters(symbol: str, market: dict, cfg: PairFilterConfig) -> bool:
    if cfg.exclude_leveraged_tokens and is_leveraged_token(symbol):
        return False

    if cfg.require_active and not market_is_active(market):
        return False

    return True


def quote_volume_usdt_from_ticker(ticker: dict) -> float | None:
    """
    Return quote volume in USDT if available.
    Many exchanges provide `quoteVolume` for tickers (24h).
    """
    qv = ticker.get("quoteVolume", None)
    if qv is None:
        return None
    try:
        return float(qv)
    except (TypeError, ValueError):
        return None
