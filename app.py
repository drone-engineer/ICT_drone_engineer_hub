import importlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Drone Hub", page_icon="🚁", layout="wide")

ROOT = Path(__file__).parent
MENU = [('safety_diagnosis', '🛰️ 사전 비행 안전 진단'), ('hybrid_rag_chat', '🤖 엔지니어링 AI 챗봇'), ('calculators', '📐 추력·비행시간 계산기'), ('preflight_check', '✅ 비행 전 점검표'), ('dev_references', '📚 개발자 레퍼런스'), ('manual_crawler', '🕷️ 스펙 수집 & 배포'), ('ops_log', '📊 질의 이력 & 엑셀')]

THEMES = {
    "☀️ 주간":  {"app_bg": "#F8FAFC", "sidebar_bg": "#FFFFFF", "text": "#0F172A", "accent": "#0284C7"},
    "🌆 황혼":  {"app_bg": "#2A1B40", "sidebar_bg": "#1F1333", "text": "#FFFBEB", "accent": "#FBBF24"},
    "🌙 야간":  {"app_bg": "#0B132B", "sidebar_bg": "#1C2541", "text": "#FFFFFF", "accent": "#38BDF8"},
}

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
    st.title("🚁 Drone Hub")
    theme_name = st.radio("테마", list(THEMES), key="app_theme", horizontal=True)
    page = st.radio("메뉴", [m for m, _ in MENU], key="app_menu",
                    format_func=lambda m: dict(MENU)[m])

t = THEMES[theme_name]
css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
for token, val in {"__APP_BG__": t["app_bg"], "__SIDEBAR_BG__": t["sidebar_bg"],
                   "__TEXT__": t["text"], "__ACCENT__": t["accent"]}.items():
    css = css.replace(token, val)
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# 한 모듈이 깨져도 앱 전체가 죽지 않도록 격리
try:
    importlib.import_module(f"modules.{page}").render()
except Exception as e:
    st.error(f"모듈 '{page}' 실행 오류")
    st.exception(e)
