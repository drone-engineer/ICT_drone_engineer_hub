import os


def secret(name, default=None):
    """Streamlit Secrets 우선, 없으면 환경변수"""
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)


FALLBACK_MODEL = "gpt-4o-mini"


def _is_reasoning(model):
    return model.startswith(("o1", "o3", "o4", "gpt-5", "gpt-6"))


def chat(messages, max_tokens=1200):
    """(답변, 사용된 모델) 반환. 기본 모델 실패 시 폴백 모델로 재시도."""
    from openai import OpenAI
    client = OpenAI(api_key=secret("OPENAI_API_KEY"))
    primary = secret("LLM_MODEL", FALLBACK_MODEL)
    last_err = None
    for model in dict.fromkeys([primary, FALLBACK_MODEL]):
        try:
            kw = {"model": model, "messages": messages}
            if _is_reasoning(model):
                kw["max_completion_tokens"] = max_tokens   # temperature는 생략
            else:
                kw["max_tokens"] = max_tokens
                kw["temperature"] = 0.2
            r = client.chat.completions.create(**kw)
            return r.choices[0].message.content, model
        except Exception as e:
            last_err = e
    raise RuntimeError(f"LLM 호출 실패: {last_err}")
