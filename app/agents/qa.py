"""Q&A agent: answer questions grounded in a meeting transcript.

Same provider switch as extraction (Gemini default, Claude optional). Free-text
answer — the model is told to answer ONLY from the transcript.
"""
from __future__ import annotations

from app.agents.extraction import get_anthropic_client, get_gemini_client, is_rate_limit
from app.config import get_settings

QA_SYSTEM = """You are a helpful meeting assistant. Answer the user's question \
using ONLY the meeting transcript provided. Be concise and specific. If the \
answer isn't in the transcript, say you don't see it discussed — do not guess."""


def _prompt(transcript: str, question: str) -> str:
    return f'Meeting transcript:\n"""\n{transcript}\n"""\n\nQuestion: {question}'


def _ask_gemini(transcript: str, question: str) -> str:
    from google.genai import types

    s = get_settings()
    client = get_gemini_client()
    resp = client.models.generate_content(
        model=s.gemini_model,
        contents=_prompt(transcript, question),
        config=types.GenerateContentConfig(system_instruction=QA_SYSTEM, temperature=0.2),
    )
    return (resp.text or "").strip()


def _ask_anthropic(transcript: str, question: str) -> str:
    s = get_settings()
    client = get_anthropic_client()
    resp = client.messages.create(
        model=s.anthropic_model, max_tokens=1024, system=QA_SYSTEM,
        messages=[{"role": "user", "content": _prompt(transcript, question)}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def answer_question(transcript: str, question: str) -> str:
    """Answer a question about the meeting. Returns plain text."""
    if not transcript or not transcript.strip():
        return "Start a meeting first — there's no transcript to answer from yet."
    if not question or not question.strip():
        return "Ask a question about the meeting."

    provider = get_settings().llm_provider.lower()
    try:
        if provider == "gemini":
            return _ask_gemini(transcript, question)
        if provider == "anthropic":
            return _ask_anthropic(transcript, question)
        raise ValueError(f"Unknown LLM_PROVIDER; expected 'gemini' or 'anthropic'.")
    except Exception as e:
        if is_rate_limit(e):
            return ("⚠️ Gemini's free tier hit its rate limit (~20 requests/minute). "
                    "Please wait about a minute, then ask again.")
        return f"⚠️ Couldn't reach the model ({type(e).__name__}). Please try again."
