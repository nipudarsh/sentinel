from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    symbol: str
    regime: str
    action: str
    note: str = ""


def print_briefing(rows: list[ReportRow]) -> None:
    if not rows:
        print("\nNo briefing rows.")
        return

    trend = [r for r in rows if r.regime == "trend" and not r.action.startswith("A+")]
    setups = [r for r in rows if r.action.startswith("A+")]
    chaos = [r for r in rows if r.regime == "chaos"]
    range_rows = [r for r in rows if r.regime == "range"]

    print("\n" + "=" * 78)
    print("SENTINEL — TRADER BRIEFING (manual execution only)")
    print("=" * 78)

    if setups:
        print("\nA+ SETUPS (prioritize)")
        print("-" * 78)
        for r in setups:
            print(f"- {r.symbol}: {r.action}  {r.note}".rstrip())

    if trend:
        print("\nTREND WATCHLIST (wait for A+ confirmation)")
        print("-" * 78)
        for r in trend[:20]:
            print(f"- {r.symbol}: {r.note}".rstrip())

    if range_rows:
        print("\nRANGE / LIMITED (avoid forcing)")
        print("-" * 78)
        for r in range_rows[:15]:
            print(f"- {r.symbol}: {r.note}".rstrip())

    if chaos:
        print("\nCHAOS (NO TRADE)")
        print("-" * 78)
        for r in chaos[:15]:
            print(f"- {r.symbol}: protect capital".rstrip())

    print("\nRISK RULES (simple + strict)")
    print("-" * 78)
    print("- Risk per trade: 1 USDT (or less) until consistency is proven.")
    print("- Only trade A+ setups. TREND alone is not an entry signal.")
    print("- After +1R: reduce risk (partial) and protect position (trail/BE).")
    print("=" * 78)
