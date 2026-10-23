import re

from utils import rag_engine as rag
from utils import router
from utils.llm import chat, secret
from utils.persona import PERSONAS

SMART, LOCAL, WEB, SIDE = "스마트 라우터", "로컬 매뉴얼 RAG", "웹 표준", "좌우 비교"
MODES = [SMART, LOCAL, WEB, SIDE]
MODE_ROUTE = {LOCAL: "manual", WEB: "web", SIDE: "compare"}

COMMON = ("답변은 한국어로 한다. 숫자 범위는 물결표(~) 대신 하이픈(-)으로 쓴다. "
          "목록 항목 사이에는 빈 줄을 둔다. 확실하지 않으면 모른다고 말하고 추측하지 않는다. "
          "비행 안전이나 결선에 영향이 있는 내용은 원문 확인을 권한다.")


def fix_md(t):
    return re.sub(r"(?<=\d)\s*~\s*(?=\d)", "-", t)


def _ask(system, user):
    txt, model = chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return fix_md(txt), model


def _manual(store, query, persona):
    if store is None:
        return "매뉴얼 인덱스가 없어 매뉴얼 검색을 할 수 없습니다.", []
    hits = rag.search(store, query)
    if not hits:
        return "제공된 매뉴얼에서 관련 내용을 찾지 못했습니다.", []
    ctx = "\n\n".join(f"[M{i}] ({h['domain']} / {h['file']} p.{h['page']})\n{h['text'][:1500]}"
                      for i, h in enumerate(hits, 1))
    system = (PERSONAS[persona] + " " + COMMON +
              " 아래 [M#] 매뉴얼 발췌만 근거로 답한다. 인용은 (파일명 p.쪽수) 형식으로 쓴다. "
              "발췌에 없는 내용은 '제공된 매뉴얼에서 찾지 못했습니다'라고 말한다.")
    ans, _ = _ask(system, f"질문: {query}\n\n매뉴얼 발췌:\n{ctx}")
    return ans, hits


def _web(query, persona):
    key = secret("TAVILY_API_KEY")
    if not key:
        return "Tavily API 키가 없어 웹 검색을 할 수 없습니다.", []
    from tavily import TavilyClient
    res = TavilyClient(api_key=key).search(query=query, search_depth="basic", max_results=5)["results"]
    if not res:
        return "웹 검색 결과가 없습니다.", []
    ctx = "\n\n".join(f"[W{i}] {r['title']} ({r['url']})\n{r['content'][:1200]}" for i, r in enumerate(res, 1))
    system = (PERSONAS[persona] + " " + COMMON +
              " 아래 [W#] 웹 검색 결과만 근거로 답하고, 근거가 된 문장 끝에 [W#] 번호를 붙인다.")
    ans, _ = _ask(system, f"질문: {query}\n\n웹 검색 결과:\n{ctx}")
    return ans, [{"title": r["title"], "url": r["url"]} for r in res]


def run(query, mode, persona, store):
    route = router.classify(query) if mode == SMART else MODE_ROUTE[mode]
    out = {"route": route, "warn": router.wiring_warning(query),
           "hits": [], "web": [], "answer": None, "tabs": None}
    if route == "manual":
        out["answer"], out["hits"] = _manual(store, query, persona)
    elif route == "web":
        out["answer"], out["web"] = _web(query, persona)
    else:
        m_ans, out["hits"] = _manual(store, query, persona)
        w_ans, out["web"] = _web(query, persona)
        system = (PERSONAS[persona] + " " + COMMON +
                  " 매뉴얼 기반 답변과 웹 기반 답변을 비교해 (1) 일치하는 점 (2) 차이나 충돌 (3) 권장 선택 "
                  "(4) 추가 확인이 필요한 사항 순서로 정리한다. 필요하면 표를 쓴다.")
        cmp_ans, _ = _ask(system, f"질문: {query}\n\n[매뉴얼 기반 답변]\n{m_ans}\n\n[웹 기반 답변]\n{w_ans}")
        out["tabs"] = {"compare": cmp_ans, "manual": m_ans, "web": w_ans}
    return out


def make_checklist(query, answer, persona):
    system = (PERSONAS[persona] + " " + COMMON +
              " 질문과 답변을 바탕으로 현장 점검표를 만든다. 4단계(1 전원·결선, 2 기체·부품, 3 설정·소프트웨어, "
              "4 비행 직전)로 나누고 각 항목은 '- [ ] ' 마크다운 체크박스로 쓴다.")
    ans, _ = _ask(system, f"질문: {query}\n\n답변:\n{answer}")
    return ans
