"""Extraction agent: transcript -> structured MeetingExtraction.

This is the brain of the system. It asks an LLM for a strict JSON schema
(structured output) so we get reliable, parseable results instead of
free-text we'd have to scrape. The provider is selectable via
``LLM_PROVIDER`` in .env ("anthropic" or "gemini") — the rest of the
pipeline consumes the same MeetingExtraction schema either way.
"""
from __future__ import annotations

import json
from functools import lru_cache

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.models import MeetingExtraction

class ExtractionError(RuntimeError):
    """Raised when the LLM output can't be parsed into a MeetingExtraction."""


def is_rate_limit(err: Exception) -> bool:
    """True if an LLM exception is a rate-limit / quota error (429)."""
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower()


# LLM clients are expensive to build (~350ms each) — create once, reuse.
_gemini_client = None
_anthropic_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=get_settings().gemini_api_key)
    return _gemini_client


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=get_settings().anthropic_api_key)
    return _anthropic_client


def _empty_extraction(summary: str) -> MeetingExtraction:
    """A valid, empty result — used when there's nothing to analyze."""
    return MeetingExtraction(summary=summary)


SYSTEM_PROMPT = """You are a meeting analyst. You read a raw meeting transcript \
and extract structured, faithful information. Rules:

- Extract ONLY what is actually said. Never invent tasks, owners, or deadlines.
- An action item is a concrete commitment to do something ("I'll send the deck",
  "Priya will fix the login bug"). Vague musings are NOT action items.
- OWNERSHIP: if a clear person is named, set owner and owner_status="resolved".
  If a name is said but it's unclear who exactly, use "unresolved". If it's
  genuinely unclear who owns it, set owner=null and owner_status="ambiguous".
  NEVER guess an owner to fill the field.
- DEADLINES: only set a date if stated or clearly implied ("by Friday").
  Convert relative dates using the meeting_date when available. Else null.
- Always include the exact source_quote the item came from.
- confidence reflects how sure you are it's a real, trackable action item.
- SUMMARY: write a thorough recap of the whole meeting — context, what was
  discussed, and how it concluded — so someone who missed it is fully caught up.
- DECISIONS: the concrete choices the group actually settled on.
- PROPOSED_SOLUTIONS: ideas/approaches suggested to solve problems raised, even
  if not yet agreed on. Keep them distinct from firm decisions.
- OPEN_QUESTIONS: unresolved threads that aren't yet tasks.

Return your answer by calling the `record_meeting_extraction` tool."""


@lru_cache(maxsize=1)
def _extraction_tool() -> dict:
    """Tool schema mirrors MeetingExtraction so the model returns valid JSON.

    Cached: computing the JSON schema on every call is wasted work.
    """
    return {
        "name": "record_meeting_extraction",
        "description": "Record the structured extraction of the meeting.",
        "input_schema": MeetingExtraction.model_json_schema(),
    }


def _build_user_content(
    transcript: str,
    meeting_title: str | None,
    meeting_date: str | None,
) -> str:
    context = ""
    if meeting_title:
        context += f"Meeting title: {meeting_title}\n"
    if meeting_date:
        context += f"Meeting date: {meeting_date}\n"
    return f'{context}\nTranscript:\n"""\n{transcript}\n"""'


def _extract_anthropic(user_content: str) -> MeetingExtraction:
    settings = get_settings()
    client = get_anthropic_client()

    tool = _extraction_tool()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            return MeetingExtraction.model_validate(block.input)

    # Fallback: try to parse any text as JSON (shouldn't normally happen).
    text = "".join(b.text for b in response.content if b.type == "text")
    return MeetingExtraction.model_validate(json.loads(text))


def _extract_gemini(user_content: str) -> MeetingExtraction:
    from google.genai import types

    settings = get_settings()
    client = get_gemini_client()

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=MeetingExtraction,
            temperature=0,
        ),
    )

    # google-genai re-validates into the Pydantic model when it can.
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, MeetingExtraction):
        return parsed
    return MeetingExtraction.model_validate(json.loads(response.text))


# Below this many non-whitespace chars there's nothing meaningful to extract.
MIN_TRANSCRIPT_CHARS = 10


def extract_meeting(
    transcript: str,
    meeting_title: str | None = None,
    meeting_date: str | None = None,
) -> MeetingExtraction:
    """Run the configured LLM on a transcript, return a validated MeetingExtraction.

    Guards malformed input: empty/whitespace/too-short transcripts short-circuit
    to an empty result (no wasted LLM call). Unparseable LLM output raises a
    clear ExtractionError instead of a raw traceback.
    """
    settings = get_settings()

    cleaned = (transcript or "").strip()
    if len(cleaned) < MIN_TRANSCRIPT_CHARS:
        return _empty_extraction(
            "No usable transcript provided — nothing to extract."
        )

    user_content = _build_user_content(transcript, meeting_title, meeting_date)
    provider = settings.llm_provider.lower()
    if provider not in ("gemini", "anthropic"):
        raise ValueError(
            f"Unknown LLM_PROVIDER {settings.llm_provider!r}; expected 'anthropic' or 'gemini'."
        )

    try:
        if provider == "gemini":
            return _extract_gemini(user_content)
        return _extract_anthropic(user_content)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ExtractionError(
            f"{provider} returned output that isn't a valid MeetingExtraction: {e}"
        ) from e
    except Exception as e:  # network / API errors -> clean, typed error
        if is_rate_limit(e):
            raise ExtractionError(
                "Rate limit: the Gemini free tier allows ~20 requests/minute. "
                "Please wait about a minute and try again."
            ) from e
        raise ExtractionError(f"{provider} request failed: {type(e).__name__}: {e}") from e
