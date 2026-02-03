from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    risk_usdt: float = 1.0
    fee_buffer_pct: float = 0.10


@dataclass(frozen=True)
class PositionSizing:
    entry: float
    stop: float
    risk_usdt: float
    stop_distance: float
    stop_distance_pct: float
    size_units: float
    notional_usdt: float


def compute_position_sizing(entry: float, stop: float, cfg: RiskConfig) -> PositionSizing | None:
    if entry <= 0 or stop <= 0 or stop >= entry:
        return None

    dist = entry - stop
    dist_adj = dist * (1.0 + cfg.fee_buffer_pct / 100.0)
    if dist_adj <= 0:
        return None

    size = cfg.risk_usdt / dist_adj
    if size <= 0:
        return None

    notional = size * entry
    dist_pct = (dist / entry) * 100.0

    return PositionSizing(
        entry=entry,
        stop=stop,
        risk_usdt=cfg.risk_usdt,
        stop_distance=dist,
        stop_distance_pct=dist_pct,
        size_units=size,
        notional_usdt=notional,
    )
