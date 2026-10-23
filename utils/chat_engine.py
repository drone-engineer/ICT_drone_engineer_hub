import re

from utils import rag_engine as rag
from utils import router
from utils.llm import chat, secret
from utils.persona import PERSONAS

SMART, LOCAL, WEB, SIDE = "스마트 라우터", "로컬 매뉴얼 RAG", "웹 표준", "로컬+웹 동시 비교"
MODES = [SMART, LOCAL, WEB, SIDE]

COMMON = ("답변은 한국어로 한다. 숫자 범위는 물결표(~) 대신 하이픈(-)으로 쓴다. "
          "목록 항목 사이에는 빈 줄을 둔다. 확실하지 않으면 모른다고 말하고 추측하지 않는다. "
          "비행 안전이나 결선에 영향이 있는 내용은 원문 확인을 권한다.")
NOT_FOUND = "제공된 매뉴얼에서 이 질문과 관련된 내용을 찾지 못했습니다."


def fix_md(t):
    return re.sub(r"(?<=\d)\s*~\s*(?=\d)", "-", t)


def _ask(system, user, max_tokens=2500):
    txt, model = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                      max_tokens=max_tokens)
    return fix_md(txt), model


# ---------- 검색 ----------
def rewrite_query(query):
    """한글 외래어 표기를 영문 원어 키워드로 보강 (실패하면 원문 그대로)"""
    try:
        txt, _ = chat([
            {"role": "system", "content":
                "드론 기술 질문을 문서 검색용 키워드로 바꾼다. 외래어 한글 표기는 영어 원어로 바꾸고"
                "(예: 아두파일럿->ArduPilot), 한국어와 영어 핵심 키워드를 한 줄로만 출력한다. 설명은 쓰지 않는다."},
            {"role": "user", "content": query}], max_tokens=300)
        line = (txt or "").strip().splitlines()[0][:200] if (txt or "").strip() else ""
        return line or query
    except Exception:
        return query


def retrieve(store, query, k=6):
    if store is None:
        return [], query
    q2 = rewrite_query(query)
    hits = rag.search(store, query, k)
    if q2 and q2 != query:
        seen = {(h["file"], h["page"]) for h in hits}
        hits += [h for h in rag.search(store, q2, k) if (h["file"], h["page"]) not in seen]
        hits = sorted(hits, key=lambda h: -h["score"])[:k]
    return hits, q2


def grade(query, hits):
    """검색된 발췌가 질문에 답할 근거가 되는지: sufficient / partial / none"""
    if not hits:
        return "none"
    ctx = "\n\n".join(f"[M{i}] ({h['file']} p.{h['page']})\n{h['text'][:700]}" for i, h in enumerate(hits, 1))
    system = ("너는 검색 결과 심사관이다. 질문과 매뉴얼 발췌를 보고 판정해 JSON 한 줄로만 답한다. "
              '형식: {"verdict":"sufficient|partial|none"}. '
              "sufficient=발췌에 질문의 핵심 대상(제품, 소프트웨어, 주제)에 대한 직접적인 답이 있다. "
              "partial=관련은 있으나 일부만 다루거나, 다른 대상의 내용이거나, 답이 모호하다. "
              "none=질문의 핵심 대상이 발췌에 없다. 이름이 비슷한 다른 제품의 내용은 sufficient가 아니다.")
    try:
        txt, _ = chat([{"role": "system", "content": system},
                       {"role": "user", "content": f"질문: {query}\n\n발췌:\n{ctx}"}], max_tokens=300)
        m = re.search(r"sufficient|partial|none", txt or "")
        return m.group(0) if m else "partial"
    except Exception:
        return "partial"


# ---------- 답변 ----------
def _manual(query, persona, hits):
    ctx = "\n\n".join(f"[M{i}] ({h['domain']} / {h['file']} p.{h['page']})\n{h['text'][:1500]}"
                      for i, h in enumerate(hits, 1))
    system = (PERSONAS[persona] + " " + COMMON +
              " 아래 [M#] 매뉴얼 발췌만 근거로 답한다. 인용은 (파일명 p.쪽수) 형식으로 쓴다. "
              "발췌가 질문의 대상과 직접 관련이 없으면 억지로 답하지 말고 '제공된 매뉴얼에서 찾지 못했습니다'라고 말한다.")
    ans, _ = _ask(system, f"질문: {query}\n\n매뉴얼 발췌:\n{ctx}")
    return ans


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


def _compare(query, persona, m_ans, w_ans):
    system = (PERSONAS[persona] + " " + COMMON +
              " 매뉴얼 기반 답변과 웹 기반 답변을 비교해 (1) 일치하는 점 (2) 차이나 충돌 (3) 권장 선택 "
              "(4) 추가 확인이 필요한 사항 순서로 정리한다. 한쪽에 근거가 없으면 그렇다고 분명히 적는다.")
    ans, _ = _ask(system, f"질문: {query}\n\n[매뉴얼 기반 답변]\n{m_ans}\n\n[웹 기반 답변]\n{w_ans}")
    return ans


def run(query, mode, persona, store):
    out = {"route": "manual", "warn": router.wiring_warning(query), "hits": [], "web": [],
           "answer": None, "tabs": None, "reason": "", "verdict": None}

    if mode == WEB:
        out["route"] = "web"
        out["answer"], out["web"] = _web(query, persona)
        return out

    hits, _ = retrieve(store, query)
    verdict = grade(query, hits)
    out["verdict"] = verdict

    def both():
        out["route"] = "compare"
        out["hits"] = hits if verdict != "none" else []
        m_ans = _manual(query, persona, hits) if verdict != "none" else NOT_FOUND
        w_ans, out["web"] = _web(query, persona)
        out["tabs"] = {"compare": _compare(query, persona, m_ans, w_ans), "manual": m_ans, "web": w_ans}

    if mode == SIDE:
        out["reason"] = "로컬과 웹을 동시에 조회해 비교했습니다"
        both()
    elif mode == LOCAL:
        if verdict == "none":
            out["answer"] = NOT_FOUND + " 웹 검색이 필요하면 '웹 표준'이나 '스마트 라우터'를 사용하세요."
            out["reason"] = "매뉴얼에 근거가 없어 답변하지 않았습니다"
        else:
            out["hits"] = hits
            out["answer"] = _manual(query, persona, hits)
            out["reason"] = ("매뉴얼 근거가 충분합니다" if verdict == "sufficient"
                             else "매뉴얼 근거가 부분적입니다. 원문을 확인하세요")
    else:   # 스마트 라우터
        if verdict == "sufficient":
            out["hits"] = hits
            out["answer"] = _manual(query, persona, hits)
            out["reason"] = "매뉴얼에 명확한 근거가 있어 로컬로 답했습니다"
        elif verdict == "none":
            out["route"] = "web"
            out["answer"], out["web"] = _web(query, persona)
            out["reason"] = "매뉴얼에 관련 내용이 없어 웹 검색으로 답했습니다"
        else:
            out["reason"] = "매뉴얼 근거가 불확실해 웹과 비교했습니다"
            both()
    return out


def make_checklist(query, answer, persona):
    system = (PERSONAS[persona] + " " + COMMON +
              " 질문과 답변을 바탕으로 현장 점검표를 만든다. 4단계(1 전원·결선, 2 기체·부품, 3 설정·소프트웨어, "
              "4 비행 직전)로 나누고 각 항목은 '- [ ] ' 마크다운 체크박스로 쓴다.")
    ans, _ = _ask(system, f"질문: {query}\n\n답변:\n{answer}")
    return ans
