import pandas as pd
import streamlit as st

from utils.ops_export import COLS, to_excel_bytes
from utils.ui import key

M = "ops"


def render():
    st.header("📊 질의 이력 & 엑셀")
    st.caption("이력은 접속한 브라우저 세션에만 저장됩니다. 새로고침하거나 오래 두면 사라지니 엑셀로 내려받으세요.")
    log = st.session_state.get("ops_log", [])
    if not log:
        st.info("아직 질의 이력이 없습니다. 챗봇에서 질문하면 여기에 쌓입니다.")
        return
    df = pd.DataFrame(log, columns=COLS)
    c1, c2, c3 = st.columns(3)
    c1.metric("전체 질의", len(df))
    c2.metric("결선 주의 질의", int((df["결선주의"] == True).sum()))
    c3.metric("비교 검증 질의", int((df["경로"] == "compare").sum()))
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.download_button("📥 질의 이력 3개 시트 엑셀 다운로드", to_excel_bytes(log),
                       file_name="drone_hub_log.xlsx", key=key(M, "dl"),
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if st.button("이력 초기화", key=key(M, "clear")):
        st.session_state["ops_log"] = []
        st.rerun()
