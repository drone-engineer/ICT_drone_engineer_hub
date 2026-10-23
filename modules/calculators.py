import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import physics as ph
from utils.ui import key

M = "calc"
BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "motors.json"


def _num(label, name, **kw):
    return st.number_input(label, key=key(M, name), **kw)


def _tab_thrust():
    c1, c2 = st.columns(2)
    with c1:
        n = st.selectbox("기체 타입 (모터 수)", [4, 6, 8], index=1, key=key(M, "t_n"))
        empty = _num("공허중량 (g, 배터리 포함)", "t_empty", min_value=100, value=8000, step=100)
        payload = _num("임무장비 중량 (g)", "t_payload", min_value=0, value=2000, step=100)
        target = st.slider("목표 추력비 (TWR)", 1.2, 3.5, 2.0, 0.1, key=key(M, "t_twr"))
    r = ph.required_thrust(empty, payload, n, target)
    with c2:
        st.metric("총 이륙중량 (AUW)", f"{r['auw']:,.0f} g")
        st.metric("요구 총 추력", f"{r['total_thrust']:,.0f} g")
        st.metric("모터 1개당 최대 추력", f"{r['per_motor_max']:,.0f} g")
        st.metric("호버링 시 모터당 추력", f"{r['per_motor_hover']:,.0f} g",
                  f"스로틀 약 {r['hover_throttle_ratio']*100:.0f}%")
    if st.button("💬 이 조건으로 AI 추천 요청", key=key(M, "t_ask")):
        st.session_state["chat_prefill"] = (
            f"{n}축 멀티콥터, 총 이륙중량 {r['auw']:.0f}g, 목표 추력비 {target}:1 입니다. "
            f"모터 1개당 최대 추력 {r['per_motor_max']:.0f}g 이상인 모터/ESC/프로펠러 조합을 추천해 주세요.")
        st.success("질문이 저장되었습니다. 챗봇 메뉴(4단계 구현 후)에서 이어집니다.")

    st.divider()
    st.subheader("추력비 판정")
    tmax = _num("선택한 모터의 최대 추력 (g/개)", "t_tmax", min_value=0, value=int(r["per_motor_max"]), step=100)
    if tmax > 0:
        v = ph.twr(n, tmax, r["auw"])
        st.metric("추력비", f"{v:.2f} : 1")
        st.write(ph.twr_grade(v))


def _tab_current():
    c1, c2 = st.columns(2)
    with c1:
        n = st.selectbox("모터 수", [4, 6, 8], index=1, key=key(M, "c_n"))
        cap = _num("배터리 용량 (mAh)", "c_cap", min_value=100, value=22000, step=500)
        s = _num("셀 수 (S)", "c_s", min_value=1, value=6, step=1)
        crate = _num("방전율 (C)", "c_c", min_value=1, value=25, step=1)
    with c2:
        dod = st.slider("사용 가능 용량 비율 (방전심도)", 0.5, 1.0, 0.8, 0.05, key=key(M, "c_dod"))
        ih = _num("모터당 호버링 전류 (A)", "c_ih", min_value=0.1, value=12.0, step=0.5)
    t = ph.hover_time_current(cap, dod, n, ih)
    imax = ph.i_max(cap, crate)
    total_i = n * ih
    m1, m2, m3 = st.columns(3)
    m1.metric("예상 호버링 시간", f"{t:.1f} 분")
    m2.metric("배터리 최대 방전 전류", f"{imax:,.0f} A")
    m3.metric("호버링 총 전류", f"{total_i:.0f} A")
    if total_i > imax:
        st.error("호버링 전류가 배터리 최대 방전 전류를 넘습니다. C-rate나 용량을 올리세요.")
    elif total_i > imax * 0.5:
        st.warning("호버링만으로 최대 방전 전류의 50%를 넘습니다. 기동 시 여유가 부족할 수 있습니다.")
    st.caption(f"{s}S 공칭 약 {s*3.7:.1f}V 기준. 사용 가능 용량 {cap/1000*dod:.1f}Ah.")


def _tab_forward():
    c1, c2 = st.columns(2)
    with c1:
        auw = _num("총 이륙중량 AUW (g)", "f_auw", min_value=100, value=10000, step=100)
        s = _num("셀 수 (S)", "f_s", min_value=1, value=6, step=1)
        cap = _num("배터리 용량 (mAh)", "f_cap", min_value=100, value=22000, step=500)
    with c2:
        dod = st.slider("방전심도", 0.5, 1.0, 0.8, 0.05, key=key(M, "f_dod"))
        eff = _num("추진 효율 (g/W)", "f_eff", min_value=1.0, value=9.0, step=0.5)
    wh = ph.battery_wh(s * 3.7, cap, dod)
    t = ph.hover_time_efficiency(auw, wh, eff)
    st.metric("예상 비행시간", f"{int(t)}분 {int((t % 1) * 60)}초")
    st.caption(f"사용 에너지 {wh:.0f} Wh, 호버링 전력 약 {auw/eff:.0f} W (셀당 공칭 3.7V 가정).")


def _tab_reverse():
    c1, c2 = st.columns(2)
    with c1:
        n = st.selectbox("모터 수", [4, 6, 8], index=1, key=key(M, "r_n"))
        base = _num("배터리 제외 기체+장비 중량 (g)", "r_base", min_value=100, value=12000, step=100)
        batt = _num("배터리 중량 (g)", "r_batt", min_value=100, value=4000, step=100)
    with c2:
        wpk = _num("배터리 에너지 밀도 (Wh/kg)", "r_wpk", min_value=50, value=180, step=10)
        dod = st.slider("방전심도", 0.5, 1.0, 0.8, 0.05, key=key(M, "r_dod"))
        target = _num("목표 비행시간 (분)", "r_t", min_value=1, value=60, step=5)
    r = ph.reverse_design(base, batt, wpk, dod, target, n)
    m1, m2, m3 = st.columns(3)
    m1.metric("실질 AUW", f"{r['auw']:,.0f} g")
    m2.metric("허용 총 전력", f"{r['power_total']:,.0f} W")
    m3.metric("모터당 허용 전력", f"{r['power_per_motor']:,.0f} W")
    st.metric("필수 최소 호버링 효율", f"{r['required_eff']:.2f} g/W")
    if r["required_eff"] > 15:
        st.error("필요 효율이 일반적인 멀티콥터 호버링 효율(대략 8-15 g/W, 경험 범위)을 크게 넘어 달성이 어렵습니다. "
                 "배터리를 늘리거나 목표 시간을 줄이세요.")
    else:
        st.success("일반적인 경험 범위 안입니다. 모터 시험표에서 이 효율 이상으로 나오는 조합을 찾으세요.")
    if st.button("💬 이 조건으로 AI 추천 요청", key=key(M, "r_ask")):
        st.session_state["chat_prefill"] = (
            f"{n}축 기체, 실질 AUW {r['auw']:.0f}g, 목표 비행시간 {target}분입니다. "
            f"필요한 호버링 효율은 {r['required_eff']:.1f} g/W, 모터당 허용 전력은 {r['power_per_motor']:.0f}W입니다. "
            "이를 만족하는 모터/프로펠러/배터리 조합을 추천해 주세요.")
        st.success("질문이 저장되었습니다. 챗봇 메뉴(4단계 구현 후)에서 이어집니다.")


def _tab_bench():
    try:
        models = json.loads(BENCH.read_text(encoding="utf-8"))["models"]
    except Exception as e:
        st.error(f"benchmarks/motors.json을 읽지 못했습니다: {e}")
        return
    names = [m["name"] for m in models]
    sel = st.selectbox("모터/프로펠러 시험 데이터", names, key=key(M, "b_model"))
    model = models[names.index(sel)]
    if model.get("sample"):
        st.warning("가상 샘플 데이터입니다. 실제 판단에 쓰지 마세요. 제조사 공식 추력표로 motors.json을 교체해야 합니다.")
    c1, c2 = st.columns(2)
    with c1:
        n = st.selectbox("모터 수", [4, 6, 8], index=1, key=key(M, "b_n"))
    with c2:
        auw = _num("총 이륙중량 AUW (g)", "b_auw", min_value=100, value=10000, step=100)
    need = auw / n
    res = ph.interp_curve(model["points"], need)
    st.write(f"호버링 시 모터당 필요 추력: **{need:,.0f} g**")
    if res is None:
        pts = model["points"]
        st.error(f"시험 데이터 범위({pts[0]['thrust_g']}-{pts[-1]['thrust_g']} g) 밖입니다. "
                 "모터 수나 모터 모델을 바꿔 보세요.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("예상 스로틀", f"{res['throttle']:.0f} %")
        m2.metric("모터당 전력", f"{res['power_w']:.0f} W")
        m3.metric("총 소모 전력", f"{res['power_w']*n:.0f} W")
        m4.metric("모터 효율", f"{res['eff_gw']:.2f} g/W")
    st.dataframe(pd.DataFrame(model["points"]).rename(columns={
        "throttle": "스로틀(%)", "thrust_g": "추력(g)", "power_w": "전력(W)"}),
        hide_index=True, use_container_width=True)


def render():
    st.header("📐 추력·비행시간 계산기")
    tabs = st.tabs(["요구 추력", "전류 기반 호버링", "효율 기반 비행시간", "목표시간 역설계", "실측 벤치마크"])
    for tab, fn in zip(tabs, [_tab_thrust, _tab_current, _tab_forward, _tab_reverse, _tab_bench]):
        with tab:
            fn()
