import pytest

from utils import chat_engine as ce

HITS = [{"domain": "01_비행제어기_FC", "file": "a.pdf", "page": 1, "text": "x", "score": 0.5}]
STATE = {"verdict": "sufficient"}


def fake_chat(messages, max_tokens=1200):
    sysm = messages[0]["content"]
    if "검색 결과 심사관" in sysm:
        return '{"verdict":"%s"}' % STATE["verdict"], "m"
    if "검색용 키워드" in sysm:
        return "ArduPilot battery", "m"
    return "ANSWER", "m"


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(ce, "chat", fake_chat)
    monkeypatch.setattr(ce.rag, "search", lambda store, q, k=6: list(HITS))
    monkeypatch.setattr(ce, "_web", lambda q, p: ("WEB", [{"title": "t", "url": "u"}]))


def run(mode, verdict):
    STATE["verdict"] = verdict
    return ce.run("질문", mode, "현장 엔지니어", store={"x": 1})


def test_smart_sufficient_local():
    o = run(ce.SMART, "sufficient")
    assert o["route"] == "manual" and o["hits"] and not o["web"]


def test_smart_none_goes_web():
    o = run(ce.SMART, "none")
    assert o["route"] == "web" and o["answer"] == "WEB" and not o["hits"]


def test_smart_partial_compare():
    o = run(ce.SMART, "partial")
    assert o["route"] == "compare" and set(o["tabs"]) == {"compare", "manual", "web"}


def test_local_none_refuses():
    o = run(ce.LOCAL, "none")
    assert "찾지 못했습니다" in o["answer"] and not o["hits"]


def test_side_always_compare_and_none_manual_tab():
    o = run(ce.SIDE, "none")
    assert o["route"] == "compare" and "찾지 못했습니다" in o["tabs"]["manual"]
    assert run(ce.SIDE, "sufficient")["route"] == "compare"


def test_web_mode_skips_retrieval():
    o = run(ce.WEB, "sufficient")
    assert o["route"] == "web" and o["verdict"] is None


def test_no_store_means_none():
    STATE["verdict"] = "sufficient"
    o = ce.run("질문", ce.SMART, "현장 엔지니어", store=None)
    assert o["route"] == "web"
