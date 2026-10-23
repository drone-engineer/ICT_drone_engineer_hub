from utils.persona import PERSONAS


def test_personas_complete():
    assert set(PERSONAS) == {"현장 엔지니어", "시스템·SW 엔지니어", "비행 안전점검관", "DIY 빌더"}
    for name, text in PERSONAS.items():
        assert "[공통 원칙]" in text and "답변 구조" in text, name
        assert "[매뉴얼]" in text and "[일반지식]" in text, name


def test_safety_has_checklist():
    assert "- [ ]" in PERSONAS["비행 안전점검관"]
