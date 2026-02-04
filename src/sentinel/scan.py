from __future__ import annotations

import argparse

from sentinel.core.config import load_config
from sentinel.core.exchange import (
    ExchangeConfig,
    ExchangeError,
    create_exchange,
    iter_usdt_symbols,
    load_markets_safe,
)
from sentinel.core.filters import (
    PairFilterConfig,
    passes_market_filters,
    quote_volume_usdt_from_ticker,
)
from sentinel.core.indicators import atr_pct, trend_strength
from sentinel.core.io import write_json, write_text
from sentinel.core.mathutils import ema
from sentinel.core.ohlcv import OHLCVConfig, fetch_ohlcv_safe, split_ohlcv
from sentinel.core.regime import MarketRegime, classify_regime
from sentinel.core.report import ReportRow, build_briefing_text
from sentinel.core.risk import RiskConfig, compute_position_sizing
from sentinel.core.setups import (
    BreakoutRetestConfig,
    PullbackConfig,
    TradePlan,
    detect_breakout_retest_long,
    detect_pullback_long,
)

_STABLE_BASES = {
    "USDT",
    "USDC",
    "FDUSD",
    "TUSD",
    "USDP",
    "BUSD",
    "DAI",
    "USD1",
    "USDE",
    "EUR",
    "EURC",
}


def is_stablecoin_pair(symbol: str) -> bool:
    base = symbol.split("/", 1)[0].upper().strip()
    return base in _STABLE_BASES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SENTINEL: scan USDT pairs (read-only).")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--limit", type=int, default=30)

    p.add_argument("--quality", action="store_true")
    p.add_argument("--min-qv", type=float, default=None)

    p.add_argument("--regime", action="store_true")
    p.add_argument("--timeframe", default="4h")
    p.add_argument("--bars", type=int, default=120)
    p.add_argument("--max-pairs", type=int, default=60)

    p.add_argument("--setups", action="store_true")
    p.add_argument("--exclude-stables", action="store_true")
    p.add_argument("--brief", action="store_true")

    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--out", default=None, help="write output to file (txt or json based on --format)")
    p.add_argument("--config", default="sentinel.toml")

    return p.parse_args()


def rank_quality_pairs(ex, markets: dict, pairs: list[str], min_qv: float) -> list[str]:
    cfg = PairFilterConfig(min_quote_volume_usdt=min_qv)

    try:
        tickers = ex.fetch_tickers()
    except Exception:
        tickers = {}

    scored: list[tuple[str, float]] = []
    for sym in pairs:
        market = markets.get(sym, {})
        if not passes_market_filters(sym, market, cfg):
            continue
        qv = quote_volume_usdt_from_ticker(tickers.get(sym, {})) or 0.0
        scored.append((sym, qv))

    scored.sort(key=lambda x: x[1], reverse=True)
    above = [s for (s, qv) in scored if qv >= min_qv]
    return above if above else [s for (s, _qv) in scored]


def compute_regime_for_symbol(ex, symbol: str, timeframe: str, bars: int) -> tuple[MarketRegime, float, float]:
    ohlcv = fetch_ohlcv_safe(ex, symbol, OHLCVConfig(timeframe=timeframe, limit=bars))
    highs, lows, closes = split_ohlcv(ohlcv)
    if not closes:
        return MarketRegime.RANGE, 0.0, 0.0

    a = atr_pct(highs, lows, closes)
    price = closes[-1]
    ema_fast = ema(closes, 20)
    ema_slow = ema(closes, 50)

    ts = trend_strength(ema_fast, ema_slow, price)
    if ts < 0.0005:
        ts = 0.0

    return classify_regime(a, ts), a, ts


def compute_setup_for_symbol(ex, symbol: str, timeframe: str, bars: int, cfg_pb: PullbackConfig, cfg_br: BreakoutRetestConfig) -> TradePlan | None:
    ohlcv = fetch_ohlcv_safe(ex, symbol, OHLCVConfig(timeframe=timeframe, limit=bars))
    highs, lows, closes = split_ohlcv(ohlcv)
    if not closes:
        return None

    plan = detect_pullback_long(closes, lows, symbol, cfg_pb)
    if plan is not None:
        return plan
    return detect_breakout_retest_long(closes, lows, symbol, cfg_br)


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)

    ex = create_exchange(ExchangeConfig(exchange_id=args.exchange))
    markets = load_markets_safe(ex)
    pairs = list(iter_usdt_symbols(markets))

    if args.exclude_stables:
        pairs = [p for p in pairs if not is_stablecoin_pair(p)]

    if args.quality:
        min_qv = cfg.min_quote_volume_usdt if args.min_qv is None else args.min_qv
        pairs = rank_quality_pairs(ex, markets, pairs, float(min_qv))

    if not args.regime:
        out_lines = [f"Exchange: {ex.id}", f"USDT pairs found: {len(pairs)}", "-" * 40]
        out_lines += sorted(pairs)[: max(args.limit, 0)]
        text = "\n".join(out_lines) + "\n"
        if args.format == "json":
            payload = {"exchange": ex.id, "count": len(pairs), "pairs": sorted(pairs)[: max(args.limit, 0)]}
            if args.out:
                write_json(args.out, payload)
            else:
                print(payload)
        else:
            if args.out:
                write_text(args.out, text)
            else:
                print(text, end="")
        return 0

    pb = PullbackConfig(
        pullback_lookback=cfg.pullback_lookback,
        pullback_tolerance_pct=cfg.pullback_tolerance_pct,
    )
    br = BreakoutRetestConfig(
        breakout_lookback=cfg.breakout_lookback,
        retest_lookback=cfg.retest_lookback,
        retest_tolerance_pct=cfg.retest_tolerance_pct,
    )
    risk_cfg = RiskConfig(risk_usdt=cfg.risk_usdt, fee_buffer_pct=cfg.fee_buffer_pct)

    pairs = pairs[: max(args.max_pairs, 0)]

    rows: list[ReportRow] = []
    table: list[dict] = []

    lines: list[str] = []
    lines.append(f"Exchange: {ex.id}")
    lines.append(f"USDT pairs found: {len(pairs)}")
    lines.append(f"Regime analysis on: {len(pairs)} pairs | tf={args.timeframe} bars={args.bars}")
    lines.append("-" * 70)
    lines.append("SYMBOL".ljust(16) + " " + "REGIME".ljust(8) + " " + "ATR%".rjust(7) + " " + "TREND".rjust(7) + "  ACTION")
    lines.append("-" * 70)

    shown = 0
    for sym in pairs:
        try:
            r, a, ts = compute_regime_for_symbol(ex, sym, args.timeframe, args.bars)
        except ExchangeError:
            continue

        plan: TradePlan | None = None
        if args.setups and r == MarketRegime.TREND:
            plan = compute_setup_for_symbol(ex, sym, args.timeframe, args.bars, pb, br)

        if plan is not None:
            action = f"A+ {plan.setup} {plan.status}"
        else:
            action = "trade-allowed" if r == MarketRegime.TREND else ("limited" if r == MarketRegime.RANGE else "NO TRADE")

        lines.append(f"{sym.ljust(16)} {r.value.ljust(8)} {a:7.2f} {ts:7.3f}  {action}")

        note = ""
        size_payload = None
        if plan is not None:
            sizing = compute_position_sizing(entry=plan.entry_ref, stop=plan.stop, cfg=risk_cfg)
            if sizing is not None:
                note = f"{plan.status}: risk {sizing.risk_usdt:.2f}, notional≈{sizing.notional_usdt:.0f}"
                size_payload = sizing
                lines.append(f"  ↳ ENTRY≈{plan.entry_ref:.6f} SL={plan.stop:.6f} TP1={plan.tp1:.6f} TP2={plan.tp2:.6f}")
                lines.append(f"     SIZE≈{sizing.size_units:.6f} units | NOTIONAL≈{sizing.notional_usdt:.2f} | STOP={sizing.stop_distance_pct:.2f}%")
                lines.append(f"     TRIGGER: {plan.entry_trigger}")
            else:
                note = f"{plan.status}: sizing unavailable"
        else:
            note = "Wait A+ (trend only)" if r == MarketRegime.TREND else ("Avoid chop" if r == MarketRegime.RANGE else "Protect capital")

        rows.append(ReportRow(symbol=sym, regime=r.value, action=action, note=note))
        table.append(
            {
                "symbol": sym,
                "regime": r.value,
                "atr_pct": a,
                "trend_strength": ts,
                "action": action,
                "plan": plan,
                "sizing": size_payload,
            }
        )

        shown += 1
        if shown >= max(args.limit, 0):
            break

    briefing_text = build_briefing_text(rows) if args.brief else ""

    if args.format == "json":
        payload = {
            "exchange": ex.id,
            "timeframe": args.timeframe,
            "bars": args.bars,
            "rows": table,
            "briefing": briefing_text,
        }
        if args.out:
            write_json(args.out, payload)
        else:
            print(payload)
    else:
        full_text = "\n".join(lines) + ("\n\n" + briefing_text if args.brief else "\n")
        if args.out:
            write_text(args.out, full_text)
        else:
            print(full_text, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
