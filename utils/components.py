"""HTML 부품 모음. 반환값은 st.markdown(..., unsafe_allow_html=True)로 그린다.
줄바꿈·들여쓰기 없이 한 줄로 만든다(마크다운이 코드블록으로 오인하는 것 방지)."""
from html import escape as _e

from utils.safety_rules import GUST_CAUTION, WIND_CAUTION, WIND_DANGER

GAUGE_MAX = 15.0


def chip(text, level=None):
    cls = f" lvl{level}" if level is not None else ""
    return f'<span class="dh-chip{cls}">{_e(str(text))}</span>'


def hero(eyebrow, title, desc="", chips=()):
    chips_html = f'<div class="dh-chips">{"".join(chips)}</div>' if chips else ""
    return (f'<div class="dh-hero"><div class="eyebrow">{_e(eyebrow)}</div>'
            f'<div class="title">{_e(title)}</div><div class="desc">{_e(desc)}</div>{chips_html}</div>')


def kpi(label, value, unit="", sub="", level=None):
    cls = f" lvl{level}" if level is not None else ""
    u = f'<span class="u">{_e(unit)}</span>' if unit else ""
    s = f'<div class="s">{_e(sub)}</div>' if sub else ""
    return (f'<div class="dh-card{cls}"><div class="k">{_e(label)}</div>'
            f'<div class="v">{_e(str(value))}{u}</div>{s}</div>')


def grid(cards):
    return f'<div class="dh-grid">{"".join(cards)}</div>'


def section(title):
    return f'<div class="dh-section">{_e(title)}</div>'


def _pct(v):
    return max(0.0, min(v / GAUGE_MAX * 100, 100.0))


def gauge_rows(rows):
    """rows: weather.parse()['rows'] (alt, wind, level, icon, label, note)"""
    marks = "".join(
        f'<div class="dh-mark" style="left:{_pct(v):.1f}%"><span>{v:g}</span></div>'
        for v in (WIND_CAUTION, WIND_DANGER))
    out = []
    for r in rows:
        note = f"<small>{_e(r['note'])}</small>" if r.get("note") else ""
        out.append(
            f'<div class="dh-grow"><div class="alt">{r["alt"]} m</div>'
            f'<div class="dh-track"><div class="dh-fill lvl{r["level"]}" style="width:{_pct(r["wind"]):.1f}%"></div>{marks}</div>'
            f'<div class="val">{r["wind"]:.1f} m/s {_e(r["icon"])}{note}</div></div>')
    return f'<div class="dh-gauges">{"".join(out)}</div>'
