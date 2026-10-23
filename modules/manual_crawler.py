import hmac
import pandas as pd
import streamlit as st

from utils import rag_engine as rag
from utils import scraper
from utils.github_sync import put_file
from utils.llm import secret
from utils.ui import key

M = "crawl"


def _domains():
    names = sorted(p.name for p in rag.MANUALS.iterdir() if p.is_dir()) if rag.MANUALS.exists() else []
    return names or ["_미분류"]


def _is_admin():
    pw = secret("ADMIN_PASSWORD")
    if not pw:
        return False
    given = st.text_input("관리자 암호 (저장·커밋 전용)", type="password", key=key(M, "pw"))
    return bool(given) and hmac.compare_digest(given, pw)


def render():
    st.header("🕷️ 스펙 수집 & 배포")
    st.caption("제조사 제품 페이지의 HTML 표를 마크다운으로 만들어 매뉴얼 폴더에 저장합니다. "
               "대상 사이트의 이용약관을 확인하세요. 자바스크립트로 그려지는 표는 읽지 못합니다.")

    url = st.text_input("제품 상세 페이지 URL", key=key(M, "url"), placeholder="https://...")
    domain = st.selectbox("저장할 계통 폴더", _domains(), key=key(M, "domain"))

    if st.button("🔎 표 수집", key=key(M, "go")) and url:
        try:
            with st.spinner("페이지를 가져오는 중..."):
                final, html = scraper.fetch_html(url.strip())
            tables = scraper.extract_tables(html)
            st.session_state[key(M, "res")] = {
                "url": final, "title": scraper.page_title(html), "tables": tables}
        except Exception as e:
            st.session_state.pop(key(M, "res"), None)
            st.error(f"수집 실패: {e}")

    res = st.session_state.get(key(M, "res"))
    if not res:
        return
    if not res["tables"]:
        st.warning("이 페이지에서 표를 찾지 못했습니다.")
        return

    st.success(f"{res['title'] or res['url']} : 표 {len(res['tables'])}개 발견")
    picks = st.multiselect("저장할 표 선택", list(range(1, len(res["tables"]) + 1)),
                           default=list(range(1, len(res["tables"]) + 1)), key=key(M, "pick"))
    chosen = [res["tables"][i - 1] for i in picks]
    for i, t in zip(picks, chosen):
        with st.expander(f"표 {i} ({t.shape[0]}행 x {t.shape[1]}열)"):
            st.dataframe(t.astype(str), use_container_width=True)
    if not chosen:
        return

    md = scraper.build_markdown(res["url"], res["title"], chosen)
    fname = f"scraped_{scraper.slug(res['url'])}.md"
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ 마크다운 다운로드", md.encode("utf-8"), file_name=fname, key=key(M, "dl_md"))
    csv = pd.concat([t.astype(str) for t in chosen], ignore_index=True).to_csv(index=False).encode("utf-8-sig")
    c2.download_button("⬇️ CSV 다운로드", csv, file_name=fname.replace(".md", ".csv"), key=key(M, "dl_csv"))

    st.divider()
    st.subheader("저장 및 배포 (관리자 전용)")
    if not secret("ADMIN_PASSWORD"):
        st.info("이 서버에는 관리자 암호가 설정되어 있지 않아 저장·배포가 잠겨 있습니다. "
                "로컬(.env의 ADMIN_PASSWORD)에서 수집한 뒤 deploy()로 올리세요.")
        return
    if not _is_admin():
        st.info("암호를 입력하면 저장·커밋 버튼이 열립니다.")
        return

    dest = rag.MANUALS / domain / fname
    if st.button("💾 매뉴얼 폴더에 저장", key=key(M, "save")):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(md, encoding="utf-8")
        st.success(f"저장 완료: manuals/{domain}/{fname}")
        st.caption("챗봇이 읽으려면 노트북에서 인덱스 빌드(셀 19)를 다시 실행해야 합니다.")

    token = secret("GITHUB_TOKEN")
    repo = secret("GITHUB_REPO", "drone-engineer/ICT_drone_engineer_hub")
    if st.button("🚀 GitHub에 커밋 (Cloud 재배포 유발)", key=key(M, "push"), disabled=not token):
        try:
            r = put_file(f"manuals/{domain}/{fname}", md.encode("utf-8"),
                         f"data: {fname} 수집", token, repo)
            st.success("이미 같은 내용입니다." if r == "same" else "커밋 완료. Cloud가 1-2분 안에 재배포합니다.")
        except Exception as e:
            st.error(str(e))
    if not token:
        st.caption("GITHUB_TOKEN이 없어 커밋 버튼이 꺼져 있습니다.")
