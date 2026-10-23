from utils.safety_rules import grade_wind, grade_kp


def test_safe():
    assert grade_wind(6.0, gust=8.0)["level"] == 0


def test_caution_wind():
    assert grade_wind(8.0)["level"] == 1


def test_caution_gust():
    assert grade_wind(5.0, gust=11.0)["level"] == 1


def test_danger_wind():
    assert grade_wind(10.0)["level"] == 2


def test_danger_gust():
    assert grade_wind(5.0, gust=13.0)["level"] == 2


def test_danger_cold_and_rain():
    assert grade_wind(3.0, temp=0.0)["level"] == 2
    assert grade_wind(3.0, precip=40)["level"] == 2


def test_kp():
    assert grade_kp(3.9)["level"] == 0
    assert grade_kp(4.0)["level"] == 1
    assert grade_kp(5.0)["level"] == 2
