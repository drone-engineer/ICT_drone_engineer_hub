import pytest
from utils import physics as p


def test_required_thrust():
    r = p.required_thrust(8000, 2000, 4, twr=2.0)
    assert r["auw"] == 10000 and r["total_thrust"] == 20000
    assert r["per_motor_max"] == 5000 and r["per_motor_hover"] == 2500


def test_twr_and_grade():
    assert p.twr(4, 2000, 4000) == 2.0
    assert "최적" in p.twr_grade(2.0)
    assert "불가" in p.twr_grade(0.9)
    assert "고기동" in p.twr_grade(3.0)


def test_i_max():
    assert p.i_max(10000, 20) == 200


def test_hover_time_current():
    assert p.hover_time_current(10000, 0.8, 4, 5) == pytest.approx(24.0)


def test_hover_time_efficiency():
    wh = p.battery_wh(22.2, 10000, 0.8)           # 177.6 Wh
    assert p.hover_time_efficiency(4000, wh, 8) == pytest.approx(21.312, rel=1e-3)


def test_reverse_roundtrip():
    r = p.reverse_design(12000, 4000, 180, 0.8, 60, 6)
    t = p.hover_time_efficiency(r["auw"], r["energy_wh"], r["required_eff"])
    assert t == pytest.approx(60.0)
    assert r["power_per_motor"] == pytest.approx(r["power_total"] / 6)


def test_interp():
    pts = [{"throttle": 30, "thrust_g": 500, "power_w": 40},
           {"throttle": 100, "thrust_g": 3000, "power_w": 600}]
    r = p.interp_curve(pts, 1750)
    assert r["throttle"] == pytest.approx(65.0)
    assert r["power_w"] == pytest.approx(320.0)
    assert p.interp_curve(pts, 100) is None
    assert p.interp_curve(pts, 5000) is None
