from utils import components as c


def test_escape():
    assert "<script>" not in c.chip("<script>alert(1)</script>")
    assert "<script>" not in c.kpi("<b>", "<i>", "<u>", "<s>")


def test_no_newlines():
    h = c.hero("E", "T", "D", [c.chip("x", 0)])
    assert "\n" not in h and "dh-hero" in h


def test_gauge_levels_and_clamp():
    rows = [{"alt": 10, "wind": 3.0, "level": 0, "icon": "G", "label": "", "note": ""},
            {"alt": 120, "wind": 99.0, "level": 2, "icon": "R", "label": "", "note": "n"}]
    h = c.gauge_rows(rows)
    assert "dh-fill lvl0" in h and "dh-fill lvl2" in h
    assert "width:100.0%" in h and "\n" not in h


def test_kpi_level_class():
    assert "dh-card lvl1" in c.kpi("a", 1, level=1)
    assert "dh-card lvl" not in c.kpi("a", 1)
