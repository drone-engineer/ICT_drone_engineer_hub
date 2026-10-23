from datetime import datetime

import streamlit as st

from utils import chat_engine as ce
from utils import rag_engine as rag
from utils.persona import PERSONAS
from utils.ui import key

M = "chat"
BADGE = {"manual": "📘 매뉴얼 RAG", "web": "🌐 실시간 웹 검색", "compare": "⚖️ 비교 대조"}
SIZE_LIMIT = 30e6


@st.cache_resource(show_spinner="매뉴얼 인덱스 불러오는 중...")
def _store():
    return rag.load()


def _sources(i, m, latest):
    hits, web = m.get("hits", []), m.get("web", [])
    if hits:
        uniq = list(dict.fromkeys((h["domain"], h["file"]) for h in hits))
        with st.expander(f"📎 참고한 매뉴얼 ({len(uniq)}개 파일)"):
            for h in hits:
                st.markdown(f"- `[{h['domain']}]` {h['file']} p.{h['page']}")
            if latest:
                for j, (dom, fname) in enumerate(uniq):
                    path = rag.MANUALS / dom / fname
                    if path.exists() and path.stat().st_size <= SIZE_LIMIT:
                        st.download_button(f"⬇️ {fname}", data=path.read_bytes(), file_name=fname,
                                           key=f"chat_dl_{i}_{j}")
    if web:
        with st.expander(f"🌐 웹 출처 ({len(web)}개)"):
            for n, r in enumerate(web, 1):
                st.markdown(f"{n}. [{r['title']}]({r['url']})")


def _render_msg(i, m, latest):
    if m["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(m["content"])
        return
    with st.chat_message("assistant", avatar="🤖"):
        if m.get("route"):
            st.caption(BADGE.get(m["route"], "") + (" · " + m["reason"] if m.get("reason") else ""))
        if m.get("warn"):
            st.warning("⚡ **[하드웨어 결선 주의]** 전원·결선은 극성 하나만 틀려도 부품이 파손됩니다. "
                       "연결 전에 제조사 원문 핀맵을 반드시 대조하세요.")
        if m.get("tabs"):
            t1, t2, t3 = st.tabs(["⚖️ 종합 비교 대조", "📘 매뉴얼 규격 내용", "🌐 웹 최신 정보"])
            t1.markdown(m["tabs"]["compare"])
            t2.markdown(m["tabs"]["manual"])
            t3.markdown(m["tabs"]["web"])
        else:
            st.markdown(m["content"])
        _sources(i, m, latest)


def render():
    st.header("🤖 엔지니어링 AI 챗봇")
    store = _store()
    c1, c2 = st.columns(2)
    with c1:
        mode = st.radio("탐색 모드", ce.MODES, key=key(M, "mode"), horizontal=True)
    with c2:
        persona = st.selectbox("페르소나", list(PERSONAS), key=key(M, "persona"))
    if store is None:
        st.warning("매뉴얼 인덱스가 없습니다. 웹 모드만 사용할 수 있습니다.")
    else:
        mt = store["meta"]
        st.caption(f"매뉴얼 인덱스: 파일 {mt['files']}개 / 청크 {mt['chunks']:,}개 (빌드 {mt['built']}). "
                   "AI 답변은 틀릴 수 있으니 결선·비행 안전 사항은 원문을 확인하세요.")

    hist = st.session_state.setdefault("chat_history", [])
    for i, m in enumerate(hist):
        _render_msg(i, m, latest=(i == len(hist) - 1))

    pending = st.session_state.pop("chat_pending", None)
    pre = st.session_state.get("chat_prefill")
    if pre:
        st.info(f"계산기에서 넘어온 질문: {pre}")
        if st.button("이 질문으로 전송", key=key(M, "send_prefill")):
            st.session_state["chat_pending"] = pre
            st.session_state["chat_prefill"] = None
            st.rerun()

    if hist and hist[-1]["role"] == "assistant":
        if st.button("✅ 이 답변으로 현장 점검표 생성", key=key(M, "mk_check")):
            last_q = next((m["content"] for m in reversed(hist) if m["role"] == "user"), "")
            last_a = hist[-1]["tabs"]["compare"] if hist[-1].get("tabs") else hist[-1]["content"]
            with st.spinner("점검표 생성 중..."):
                try:
                    md = ce.make_checklist(last_q, last_a, persona)
                    hist.append({"role": "assistant", "content": md, "route": None})
                    st.rerun()
                except Exception as e:
                    st.error(f"점검표 생성 실패: {e}")

    q = st.chat_input("질문을 입력하세요 (예: Pixhawk 6C 전원 모듈 VCC/GND 핀 순서는?)") or pending
    if q:
        hist.append({"role": "user", "content": q})
        with st.chat_message("user", avatar="👤"):
            st.markdown(q)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("답변 생성 중..."):
                try:
                    out = ce.run(q, mode, persona, store)
                except Exception as e:
                    st.error(f"답변 생성 실패: {e}")
                    hist.pop()
                    return
        text = out["tabs"]["compare"] if out["tabs"] else out["answer"]
        hist.append({"role": "assistant", "content": out["answer"] or "", "route": out["route"], "reason": out.get("reason", ""),
                     "warn": out["warn"], "tabs": out["tabs"], "hits": out["hits"], "web": out["web"]})
        st.session_state.setdefault("ops_log", []).append({
            "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "질문": q, "경로": out["route"],
            "페르소나": persona, "계통": ", ".join(sorted({h["domain"] for h in out["hits"]})),
            "결선주의": out["warn"], "답변요약": (text or "")[:200]})
        st.rerun()
