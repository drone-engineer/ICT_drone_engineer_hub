from datetime import datetime, timezone

from utils import airspace, space_weather, weather


def fake_js():
    return {"utc_offset_seconds": 32400, "hourly": {
        "time": ["2026-10-23T08:00", "2026-10-23T09:00"],
        "wind_speed_10m": [2, 4.0], "wind_speed_80m": [3, 8.0],
        "wind_speed_120m": [3, 9.0], "wind_speed_180m": [4, 10.5],
        "wind_gusts_10m": [5, 6.0], "temperature_2m": [10, 12.0],
        "precipitation_probability": [0, 10]}}


def test_interp_40m_between():
    v = weather.interp_40m(4.0, 8.0)
    assert 4.0 < v < 8.0
    assert abs(v - 6.35) < 0.05


def test_interp_zero_safe():
    assert weather.interp_40m(0.0, 6.0) > 0


def test_parse_levels():
    now = datetime(2026, 10, 23, 0, 10, tzinfo=timezone.utc)   # 현지 09:10
    r = weather.parse(fake_js(), now_utc=now)
    assert r["time"] == "2026-10-23T09:00"
    lv = {x["alt"]: x["level"] for x in r["rows"]}
    assert lv[10] == 0 and lv[80] == 1 and lv[120] == 1 and lv[180] == 2


def test_kp_both_formats():
    assert space_weather.parse_kp([["time_tag", "Kp"], ["2026-10-23 00:00:00", "3.33"]])[1] == 3.33
    assert space_weather.parse_kp([{"time_tag": "t", "Kp": 4.0}])[1] == 4.0


def test_airspace_gimpo_inside():
    names = [n for _, n, _ in airspace.inside_zones(37.558, 126.791)]
    assert any("김포" in n for n in names)


def test_airspace_far_outside():
    assert airspace.inside_zones(36.00, 127.80) == []
