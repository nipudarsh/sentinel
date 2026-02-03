from __future__ import annotations

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
from sentinel.core.mathutils import ema
from sentinel.core.ohlcv import OHLCVConfig, fetch_ohlcv_safe, split_ohlcv
from sentinel.core.regime import MarketRegime, classify_regime
from sentinel.core.report import ReportRow, build_briefing_text
from sentinel.core.risk import RiskConfig, compute_position_sizing
from sentinel.core.setups import (
    BreakoutRetestConfig,
    PullbackConfig,
    detect_breakout_retest_long,
    detect_pullback_long,
)
from sentinel.ui.presets import get_preset
from sentinel.ui.schemas import ScanRequest, ScanResponse, ScanRow

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


def _is_stablecoin_pair(symbol: str) -> bool:
    base = symbol.split("/", 1)[0].upper().strip()
    return base in _STABLE_BASES


def _rank_quality_pairs(ex, markets: dict, pairs: list[str], min_qv: float) -> list[str]:
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


def _compute_regime(ex, symbol: str, timeframe: str, bars: int) -> tuple[MarketRegime, float, float]:
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


def _compute_setup(ex, symbol: str, timeframe: str, bars: int, pb: PullbackConfig, br: BreakoutRetestConfig):
    ohlcv = fetch_ohlcv_safe(ex, symbol, OHLCVConfig(timeframe=timeframe, limit=bars))
    highs, lows, closes = split_ohlcv(ohlcv)
    if not closes:
        return None

    plan = detect_pullback_long(closes, lows, symbol, pb)
    if plan is not None:
        return plan
    return detect_breakout_retest_long(closes, lows, symbol, br)


def run_scan(req: ScanRequest) -> ScanResponse:
    preset = get_preset(req.preset)

    timeframe = req.timeframe or preset.timeframe
    bars = req.bars or preset.bars
    refresh_seconds = req.refresh_seconds or preset.refresh_seconds
    max_pairs = req.max_pairs or preset.max_pairs

    ex = create_exchange(ExchangeConfig(exchange_id=req.exchange))
    markets = load_markets_safe(ex)
    pairs = list(iter_usdt_symbols(markets))

    if req.exclude_stables:
        pairs = [p for p in pairs if not _is_stablecoin_pair(p)]

    if req.quality:
        pairs = _rank_quality_pairs(ex, markets, pairs, req.min_qv)

    pairs = pairs[: max(max_pairs, 0)]

    pb = PullbackConfig(
        pullback_lookback=14,
        pullback_tolerance_pct=2.2,
    )
    br = BreakoutRetestConfig(
        breakout_lookback=40,
        retest_lookback=10,
        retest_tolerance_pct=1.0,
    )

    risk_cfg = RiskConfig(risk_usdt=req.risk_usdt, fee_buffer_pct=req.fee_buffer_pct)

    rows: list[ScanRow] = []
    briefing_rows: list[ReportRow] = []

    shown = 0
    for sym in pairs:
        try:
            r, a, ts = _compute_regime(ex, sym, timeframe, bars)
        except ExchangeError:
            continue

        plan = None
        if req.setups and r == MarketRegime.TREND:
            try:
                plan = _compute_setup(ex, sym, timeframe, bars, pb, br)
            except Exception:
                plan = None

        if plan is not None:
            action = f"A+ {plan.setup} {plan.status}"
            sizing = compute_position_sizing(entry=plan.entry_ref, stop=plan.stop, cfg=risk_cfg)
            if sizing is not None:
                note = f"risk {sizing.risk_usdt:.2f} | notional≈{sizing.notional_usdt:.0f} | SL {sizing.stop_distance_pct:.2f}%"
            else:
                note = "sizing unavailable"
        else:
            action = (
                "trade-allowed"
                if r == MarketRegime.TREND
                else ("limited" if r == MarketRegime.RANGE else "NO TRADE")
            )
            note = (
                "Trend only → wait A+"
                if r == MarketRegime.TREND
                else ("Range → avoid chop" if r == MarketRegime.RANGE else "Chaos → protect capital")
            )

        rows.append(ScanRow(symbol=sym, regime=r.value, atr_pct=float(a), trend_strength=float(ts), action=action, note=note))
        briefing_rows.append(ReportRow(symbol=sym, regime=r.value, action=action, note=note))

        shown += 1
        if shown >= max(req.limit, 0):
            break

    briefing = build_briefing_text(briefing_rows) if req.brief else ""
    return ScanResponse(
        exchange=ex.id,
        timeframe=timeframe,
        bars=bars,
        refresh_seconds=refresh_seconds,
        rows=rows,
        briefing=briefing,
    )
