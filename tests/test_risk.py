from sentinel.core.risk import RiskConfig, compute_position_sizing


def test_position_sizing_basic():
    cfg = RiskConfig(risk_usdt=1.0, fee_buffer_pct=0.0)
    s = compute_position_sizing(entry=100.0, stop=99.0, cfg=cfg)
    assert s is not None
    assert abs(s.size_units - 1.0) < 1e-9
    assert abs(s.notional_usdt - 100.0) < 1e-9
