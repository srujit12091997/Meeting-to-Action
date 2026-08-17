"""Run the extraction pipeline on a transcript file and print the result.

Usage (needs ANTHROPIC_API_KEY in .env):
    python scripts/run_extraction.py tests/sample_transcripts/standup_example.txt \
        --owners Sarah Raj Priya Mike

This is our Days 1-3 iteration harness: run it on each sample transcript,
eyeball the JSON, tweak the prompt in app/agents/extraction.py, repeat.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.graph.build import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract action items from a transcript.")
    parser.add_argument("transcript", help="Path to a .txt transcript file")
    parser.add_argument("--title", default=None)
    parser.add_argument("--date", default=None, help="Meeting date YYYY-MM-DD")
    parser.add_argument("--owners", nargs="*", default=[], help="Known team members")
    args = parser.parse_args()

    text = Path(args.transcript).read_text(encoding="utf-8")
    result = pipeline.invoke(
        {
            "transcript": text,
            "meeting_title": args.title,
            "meeting_date": args.date,
            "known_owners": args.owners,
        }
    )

    ext = result["extraction"]
    print("=" * 60)
    print(f"SUMMARY: {ext.summary}\n")
    print(f"DECISIONS ({len(ext.decisions)}):")
    for d in ext.decisions:
        print(f"  - {d}")
    print(f"\nACTION ITEMS ({len(ext.action_items)}):")
    for a in ext.action_items:
        flag = "" if a.owner_status.value == "resolved" else f"  [{a.owner_status.value.upper()}]"
        print(f"  - {a.task}{flag}")
        print(f"      owner={a.owner!r}  deadline={a.deadline}  conf={a.confidence}")
        print(f"      quote: \"{a.source_quote}\"")
    if ext.open_questions:
        print(f"\nOPEN QUESTIONS ({len(ext.open_questions)}):")
        for q in ext.open_questions:
            print(f"  - {q}")
    print("=" * 60)
    print(f"NEEDS HUMAN REVIEW: {result.get('needs_review')}")


if __name__ == "__main__":
    sys.exit(main())
