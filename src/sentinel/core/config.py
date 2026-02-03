from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SentinelConfig:
    risk_usdt: float = 1.0
    fee_buffer_pct: float = 0.10

    min_quote_volume_usdt: float = 5_000_000.0

    # setups
    pullback_lookback: int = 14
    pullback_tolerance_pct: float = 2.2

    breakout_lookback: int = 40
    retest_lookback: int = 10
    retest_tolerance_pct: float = 1.0


def load_config(path: str = "sentinel.toml") -> SentinelConfig:
    p = Path(path)
    if not p.exists():
        return SentinelConfig()

    try:
        import tomllib  # py3.11+
    except Exception:
        tomllib = None

    if tomllib is None:
        return SentinelConfig()

    data = tomllib.loads(p.read_text(encoding="utf-8")) or {}

    def get(section: str, key: str, default):
        return (data.get(section, {}) or {}).get(key, default)

    return SentinelConfig(
        risk_usdt=float(get("risk", "risk_usdt", 1.0)),
        fee_buffer_pct=float(get("risk", "fee_buffer_pct", 0.10)),
        min_quote_volume_usdt=float(get("quality", "min_quote_volume_usdt", 5_000_000.0)),
        pullback_lookback=int(get("setups", "pullback_lookback", 14)),
        pullback_tolerance_pct=float(get("setups", "pullback_tolerance_pct", 2.2)),
        breakout_lookback=int(get("setups", "breakout_lookback", 40)),
        retest_lookback=int(get("setups", "retest_lookback", 10)),
        retest_tolerance_pct=float(get("setups", "retest_tolerance_pct", 1.0)),
    )
