from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    symbol: str
    regime: str
    action: str
    note: str = ""


def build_briefing_text(rows: list[ReportRow]) -> str:
    if not rows:
        return "No briefing rows.\n"

    trend = [r for r in rows if r.regime == "trend" and not r.action.startswith("A+")]
    setups = [r for r in rows if r.action.startswith("A+")]
    chaos = [r for r in rows if r.regime == "chaos"]
    ranges = [r for r in rows if r.regime == "range"]

    out: list[str] = []
    out.append("=" * 78)
    out.append("SENTINEL — TRADER BRIEFING (manual execution only)")
    out.append("=" * 78)

    if setups:
        out.append("\nA+ SETUPS (prioritize)")
        out.append("-" * 78)
        for r in setups:
            out.append(f"- {r.symbol}: {r.action}  {r.note}".rstrip())

    if trend:
        out.append("\nTREND WATCHLIST (wait for A+ confirmation)")
        out.append("-" * 78)
        for r in trend[:20]:
            out.append(f"- {r.symbol}: {r.note}".rstrip())

    if ranges:
        out.append("\nRANGE / LIMITED (avoid forcing)")
        out.append("-" * 78)
        for r in ranges[:15]:
            out.append(f"- {r.symbol}: {r.note}".rstrip())

    if chaos:
        out.append("\nCHAOS (NO TRADE)")
        out.append("-" * 78)
        for r in chaos[:15]:
            out.append(f"- {r.symbol}: protect capital".rstrip())

    out.append("\nRISK RULES (v1)")
    out.append("-" * 78)
    out.append("- Risk per trade: keep small (default 1 USDT).")
    out.append("- Daily rule: stop after -2R.")
    out.append("- Only trade A+ setups. TREND alone is not an entry.")
    out.append("=" * 78)
    return "\n".join(out) + "\n"
