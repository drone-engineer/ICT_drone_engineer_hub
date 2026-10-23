import pandas as pd
import streamlit as st

from utils import airspace, geocode, space_weather, weather
from utils.safety_rules import LEGAL_ALT_M, LEVELS, grade_kp
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

    st.caption(f"현재 위치: **{ss['loc_name']}** ({ss['loc_lat']:.4f}, {ss['loc_lon']:.4f})")


def render():
    st.header("🛰️ 사전 비행 안전 진단")
    _location_picker()
    lat, lon = st.session_state["loc_lat"], st.session_state["loc_lon"]

    # ---- 상공 기상 ----
    try:
        wx = _wx(lat, lon)
    except Exception as e:
        st.error(f"기상 데이터를 불러오지 못했습니다: {e}")
        wx = None

    if wx:
        alts = [r["alt"] for r in wx["rows"]]
        sel = st.select_slider("판정 기준 고도 (m)", options=alts, value=120, key=key(M, "alt"))
        row = next(r for r in wx["rows"] if r["alt"] == sel)

        c1, c2 = st.columns(2)
        with c1:
            st.metric(f"{row['icon']} {sel}m 종합 판정", row["label"])
            for reason in row["reasons"]:
                st.caption("• " + reason)
        with c2:
            try:
                t, kp = _kp()
                g = grade_kp(kp)
                st.metric(f"{g['icon']} 지자기 Kp", f"{kp:.1f}", g["label"])
            except Exception as e:
                st.warning(f"Kp 데이터를 불러오지 못했습니다: {e}")

        m1, m2, m3 = st.columns(3)
        m1.metric("기온", f"{wx['temp']:.1f} ℃" if wx["temp"] is not None else "-")
        m2.metric("강수확률", f"{wx['precip']:.0f} %" if wx["precip"] is not None else "-")
        m3.metric("10m 순간돌풍", f"{wx['gust']:.1f} m/s" if wx["gust"] is not None else "-")

        df = pd.DataFrame([{
            "고도(m)": r["alt"], "풍속(m/s)": round(r["wind"], 1),
            "판정": f"{r['icon']} {r['label']}", "비고": r["note"]} for r in wx["rows"]])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.caption(f"기준 시각 {wx['time']} (현지). 돌풍은 10m 값만 제공되어 모든 고도 판정에 동일 적용됩니다. "
                   f"법정 한계 고도는 지표면 기준 {LEGAL_ALT_M}m입니다.")

    # ---- 공역 ----
    st.subheader("🗺️ 항공 공역")
    hits = airspace.inside_zones(lat, lon)
    if hits:
        for kind, name, d in hits:
            (st.error if kind in ("P", "R") else st.warning)(
                f"현재 위치는 **[{kind}] {name}** 범위 안으로 보입니다 (중심까지 {d:.1f}km). 비행 승인 여부를 확인하세요.")
    else:
        st.success("개략 데이터 기준으로 P/R/CTR 구역 밖입니다. (공식 확인 필수)")
    from streamlit_folium import st_folium
    st_folium(airspace.build_map(lat, lon), height=520, use_container_width=True,
              returned_objects=[], key=key(M, "map"))
    st.caption("🔴 P(비행금지) · 🟠 R(비행제한) · 🔵 CTR(공항 관제권)  |  " + airspace.DISCLAIMER)
