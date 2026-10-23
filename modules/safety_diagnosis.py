import streamlit as st

from utils import airspace, geocode, space_weather, weather
from utils import components as ui_c
from utils.safety_rules import LEGAL_ALT_M, grade_kp
from utils.ui import key

M = "safety"


@st.cache_data(ttl=600, show_spinner=False)
def _wx(lat, lon):
    return weather.fetch(round(lat, 3), round(lon, 3))


@st.cache_data(ttl=600, show_spinner=False)
def _kp():
    return space_weather.fetch_kp()


def _set_loc(name, lat, lon):
    st.session_state["loc_name"] = name
    st.session_state["loc_lat"] = lat
    st.session_state["loc_lon"] = lon


def _location_picker():
    ss = st.session_state
    ss.setdefault("loc_name", "판교")
    ss.setdefault("loc_lat", geocode.PRESETS["판교"][0])
    ss.setdefault("loc_lon", geocode.PRESETS["판교"][1])

    c1, c2, c3 = st.columns([2, 3, 1])
    with c1:
        pick = st.selectbox("비행 거점 프리셋", ["(선택)"] + list(geocode.PRESETS), key=key(M, "preset"))
        if pick != "(선택)" and ss.get(key(M, "last_preset")) != pick:
            ss[key(M, "last_preset")] = pick
            _set_loc(pick, *geocode.PRESETS[pick])
    with c2:
        q = st.text_input("주소·지명 검색 (입력 후 Enter)", key=key(M, "query"),
                          placeholder="예: 단양, 경기도 화성시 우정읍")
        if q and ss.get(key(M, "last_query")) != q:
            ss[key(M, "last_query")] = q
            try:
                res = geocode.geocode(q)
                if res:
                    _set_loc(*res)
                else:
                    st.warning("검색 결과가 없습니다.")
            except Exception as e:
                st.warning(f"주소 검색 실패: {e}")
    with c3:
        st.write("")
        st.write("")
        if st.button("📍 내 위치", key=key(M, "gps_btn")):
            ss[key(M, "gps_req")] = True

    if ss.get(key(M, "gps_req")):
        try:
            from streamlit_js_eval import get_geolocation
            loc = get_geolocation(component_key=key(M, "gps"))
            if loc and "coords" in loc:
                _set_loc("현재 위치(GPS)", loc["coords"]["latitude"], loc["coords"]["longitude"])
                ss[key(M, "gps_req")] = False
                st.rerun()
            else:
                st.info("브라우저의 위치 권한을 허용해 주세요. 허용 후 잠시 기다리면 갱신됩니다.")
        except Exception as e:
            st.warning(f"GPS를 사용할 수 없습니다: {e}")
            ss[key(M, "gps_req")] = False


def render():
    with st.expander("📍 위치 설정", expanded=False):
        _location_picker()
    name = st.session_state["loc_name"]
    lat, lon = st.session_state["loc_lat"], st.session_state["loc_lon"]

    try:
        wx = _wx(lat, lon)
    except Exception as e:
        st.markdown(ui_c.hero("PRE-FLIGHT BRIEFING", "사전 비행 안전 진단", f"{name} ({lat:.3f}, {lon:.3f})"),
                    unsafe_allow_html=True)
        st.error(f"기상 데이터를 불러오지 못했습니다: {e}")
        return

    alts = [r["alt"] for r in wx["rows"]]
    sel = st.select_slider("판정 기준 고도 (m)", options=alts, value=120, key=key(M, "alt"))
    row = next(r for r in wx["rows"] if r["alt"] == sel)

    try:
        _, kp = _kp()
        gk = grade_kp(kp)
    except Exception:
        kp, gk = None, None

    chips = [ui_c.chip(f"{row['icon']} {sel}m {row['label']}", row["level"])]
    if gk:
        chips.append(ui_c.chip(f"{gk['icon']} Kp {kp:.1f} {gk['label']}", gk["level"]))
    hits = airspace.inside_zones(lat, lon)
    if hits:
        chips.append(ui_c.chip(f"🚧 {hits[0][1]} 범위", 2 if hits[0][0] in ("P", "R") else 1))
    st.markdown(ui_c.hero("PRE-FLIGHT BRIEFING", "사전 비행 안전 진단",
                          f"{name} ({lat:.3f}, {lon:.3f}) · 기준 시각 {wx['time'].replace('T', ' ')} (현지)",
                          chips), unsafe_allow_html=True)

    tab_wx, tab_air = st.tabs(["🌬️ 상공 기상", "🗺️ 항공 공역"])

    with tab_wx:
        cards = [ui_c.kpi(f"{sel}m 풍속", f"{row['wind']:.1f}", "m/s", row["label"], row["level"])]
        cards.append(ui_c.kpi("기온", f"{wx['temp']:.1f}" if wx["temp"] is not None else "-", "℃",
                              "0℃ 이하 LiPo 주의"))
        cards.append(ui_c.kpi("강수확률", f"{wx['precip']:.0f}" if wx["precip"] is not None else "-", "%",
                              "40% 이상 비행 금지"))
        cards.append(ui_c.kpi("10m 순간돌풍", f"{wx['gust']:.1f}" if wx["gust"] is not None else "-", "m/s",
                              "전 고도 판정에 동일 적용"))
        if gk:
            cards.append(ui_c.kpi("지자기 Kp", f"{kp:.1f}", "", gk["label"], gk["level"]))
        st.markdown(ui_c.grid(cards), unsafe_allow_html=True)

        if row["reasons"]:
            st.warning("판정 사유: " + " / ".join(row["reasons"]))

        st.markdown(ui_c.section("고도별 풍속 프로파일"), unsafe_allow_html=True)
        st.markdown(ui_c.gauge_rows(wx["rows"]), unsafe_allow_html=True)
        st.markdown(f'<div class="dh-note">눈금선은 주의(7 m/s)·금지(10 m/s) 기준입니다. '
                    f'법정 한계 고도는 지표면 기준 {LEGAL_ALT_M}m이며 40m는 보간 추정값입니다.</div>',
                    unsafe_allow_html=True)

    with tab_air:
        if hits:
            for kind, nm, d in hits:
                (st.error if kind in ("P", "R") else st.warning)(
                    f"현재 위치는 **[{kind}] {nm}** 범위 안으로 보입니다 (중심까지 {d:.1f}km). 비행 승인 여부를 확인하세요.")
        else:
            st.success("개략 데이터 기준으로 P/R/CTR 구역 밖입니다. (공식 확인 필수)")
        from streamlit_folium import st_folium
        st_folium(airspace.build_map(lat, lon), height=520, use_container_width=True,
                  returned_objects=[], key=key(M, "map"))
        st.caption("🔴 P(비행금지) · 🟠 R(비행제한) · 🔵 CTR(공항 관제권)  |  " + airspace.DISCLAIMER)
