from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    symbol: str
    regime: str
    action: str
    note: str = ""


def print_report(rows: list[ReportRow]) -> None:
    if not rows:
        print("No rows.")
        return

    print("-" * 78)
    print("SENTINEL BRIEFING")
    print("-" * 78)

    for r in rows:
        line = f"{r.symbol.ljust(16)} {r.regime.ljust(7)} {r.action.ljust(18)} {r.note}"
        print(line)

    print("-" * 78)
    print("TASKS (manual execution only)")
    print("-" * 78)
    for r in rows:
        if r.action.startswith("A+"):
            print(f"- {r.symbol}: follow the plan; risk small; wait confirmation; journal result")
        elif r.regime == "trend":
            print(f"- {r.symbol}: set alerts; wait for an A+ setup (no forcing)")
        elif r.regime == "chaos":
            print(f"- {r.symbol}: NO TRADE (protect capital)")
