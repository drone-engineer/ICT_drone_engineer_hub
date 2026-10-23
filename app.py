import importlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Drone Hub", page_icon="🚁", layout="wide")

ROOT = Path(__file__).parent
MENU = [('safety_diagnosis', '🛰️ 사전 비행 안전 진단'), ('hybrid_rag_chat', '🤖 엔지니어링 AI 챗봇'), ('calculators', '📐 추력·비행시간 계산기'), ('preflight_check', '✅ 비행 전 점검표'), ('dev_references', '📚 개발자 레퍼런스'), ('manual_crawler', '🕷️ 스펙 수집 & 배포'), ('ops_log', '📊 질의 이력 & 엑셀')]

THEMES = {
    "☀️ 주간": {"bg": "#F1F5F9", "sidebar": "#FFFFFF", "text": "#0F172A", "muted": "#64748B",
               "accent": "#0284C7", "card": "#FFFFFF", "border": "#E2E8F0",
               "hero1": "#E0F2FE", "hero2": "#F8FAFC"},
    "🌆 황혼": {"bg": "#2A1B40", "sidebar": "#1F1333", "text": "#FFFBEB", "muted": "#C4B5D6",
               "accent": "#FBBF24", "card": "#3A2757", "border": "#54397A",
               "hero1": "#4A2F73", "hero2": "#2A1B40"},
    "🌙 야간": {"bg": "#0B132B", "sidebar": "#111B3A", "text": "#F8FAFC", "muted": "#94A3B8",
               "accent": "#38BDF8", "card": "#16213E", "border": "#26365F",
               "hero1": "#12305A", "hero2": "#0B132B"},
}
STATUS = {"ok": "#22C55E", "warn": "#F59E0B", "danger": "#EF4444"}

# 브라우저 자동번역으로 인한 React DOM 오류 방지
components.html("""
<script>
const d = window.parent.document;
d.documentElement.setAttribute("translate", "no");
d.documentElement.classList.add("notranslate");
if (!d.querySelector('meta[name="google"]')) {
  const m = d.createElement("meta"); m.name = "google"; m.content = "notranslate"; d.head.appendChild(m);
}
</script>""", height=0)

with st.sidebar:
    st.markdown('<div class="dh-brand"><div class="logo">🚁</div><div>'
                '<div class="name">Drone Hub</div><div class="sub">UAV OPS &amp; ENGINEERING</div>'
                '</div></div>', unsafe_allow_html=True)
    theme_name = st.radio("테마", list(THEMES), index=2, key="app_theme", horizontal=True)
    page = st.radio("메뉴", [m for m, _ in MENU], key="app_menu", format_func=lambda m: dict(MENU)[m])
    st.divider()
    st.caption("데이터: Open-Meteo · NOAA SWPC · OpenStreetMap\n\n비행 전 최종 판단과 책임은 조종자에게 있습니다.")

t = THEMES[theme_name]
vars_css = ":root{" + ";".join(f"--{k}:{v}" for k, v in {**t, **STATUS}.items()) + "}"
css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{vars_css}\n{css}</style>", unsafe_allow_html=True)

try:
    importlib.import_module(f"modules.{page}").render()
except Exception as e:
    st.error(f"모듈 '{page}' 실행 오류")
    st.exception(e)
