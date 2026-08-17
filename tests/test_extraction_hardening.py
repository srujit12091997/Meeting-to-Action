"""Malformed-input hardening for extraction (all offline, no LLM calls).

Covers: empty / whitespace / too-short transcripts short-circuit safely, and
unparseable LLM output surfaces a clear ExtractionError.
"""
import json

import pytest

import app.agents.extraction as extraction
from app.agents.extraction import ExtractionError, extract_meeting
from app.graph.build import build_pipeline


def test_empty_transcript_returns_empty():
    ext = extract_meeting("")
    assert ext.action_items == []
    assert ext.decisions == []
    assert "nothing to extract" in ext.summary.lower()


def test_whitespace_transcript_returns_empty():
    ext = extract_meeting("   \n\t  ")
    assert ext.action_items == []


def test_too_short_transcript_returns_empty():
    # Below MIN_TRANSCRIPT_CHARS -> guarded, no LLM call.
    ext = extract_meeting("hi all")
    assert ext.action_items == []


def test_bad_llm_output_raises_extraction_error(monkeypatch):
    def boom(_content):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(extraction, "_extract_gemini", boom)
    monkeypatch.setattr(extraction, "_extract_anthropic", boom)

    with pytest.raises(ExtractionError):
        extract_meeting("This is a long enough transcript to pass the guard.")


def test_pipeline_handles_empty_transcript():
    # Real extract_meeting runs, but the empty guard means no LLM/key needed.
    result = build_pipeline().invoke({"transcript": "", "known_owners": []})
    assert result["extraction"].action_items == []
    assert result.get("needs_review") is False
