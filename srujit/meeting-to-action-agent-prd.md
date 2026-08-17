# Meeting-to-Action Agent: Product Planning Document

**Owner:** [Your Name]
**Status:** Planning
**Target:** Portfolio project for AI Engineer roles (2026)

---

## 1. Problem Statement

Teams lose the majority of what's decided and committed to in meetings because no one reliably captures it. Action items mentioned verbally ("I'll take a look at that") rarely make it into a tracked task with a clear owner and deadline, and nothing follows up when they go stale. This project builds an agent that closes that loop end-to-end: transcript in, tracked and followed-up tasks out.

## 2. Target User

Small teams (3-10 people) running regular meetings (standups, planning, client calls) who already use a lightweight task tool (Notion or Asana) but have no reliable way to turn conversation into tracked work.

## 3. Goals

| Goal | Why it matters |
|---|---|
| Extract accurate action items + owners from a transcript | Core value proposition |
| Push tasks into a real external tool automatically | Proves the system *acts*, not just summarizes, this is the "agent" signal |
| Autonomously follow up on stale tasks | Demonstrates ongoing, autonomous agent behavior, the strongest interview talking point |
| Ship a working, demoable v1 fast | Portfolio value comes from a finished, demoable system, not partial builds |

**Non-goals (explicitly out of scope for v1):** live/real-time meeting transcription, multi-language support, calendar scheduling, auto-sending messages without human review.

## 4. Scope: MVP vs. Stretch

To compress this into fewer cycles, the project is split into a **hard MVP boundary** and **stretch goals** you only touch once the MVP is fully working end-to-end.

### MVP (must ship: this alone is a complete, demoable project)
- Accepts a **text transcript** (upload or paste), no audio/Whisper in MVP
- LLM extracts structured JSON: decisions, action items, owner, deadline
- Explicit handling of ambiguous ownership (flagged, not guessed)
- Pushes tasks into **one** external tool (pick Notion **or** Asana, not both)
- Simple Streamlit UI: upload transcript → see extracted tasks → confirm → push
- One documented follow-up mechanism: a script that checks task status and **drafts** (does not send) a nudge message for stale items

### Stretch (only after MVP works reliably end-to-end)
- Audio input via Whisper + speaker diarization
- Auto-send follow-up nudges via Slack/email API
- Weekly digest email
- Second tool integration (both Notion and Asana)
- Multi-meeting analytics dashboard (who has the most open action items, etc.)

This structure means you have a **complete, demoable product after Cycle 1**, the stretch items are additive polish, not required for the story to make sense in an interview.

## 5. System Architecture

```
Transcript (text)
      ↓
Extraction Agent (LLM, structured JSON output)
      ↓
Owner Resolution (name-matching + ambiguity flagging)
      ↓
Review UI (human confirms before anything is pushed)
      ↓
Task Sync (Notion/Asana API)
      ↓
Follow-up Checker (scheduled) → drafts nudge for stale tasks
```

**Key design principle:** human confirms before any external write (push tasks, send nudges). This is both a safety practice and a strong point to raise in interviews about responsible agent design.

## 6. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Extraction/reasoning | Google Gemini (free tier), or Claude, JSON structured output | Reliable structured extraction; Gemini keeps it zero-cost |
| Task integration | Notion API (recommended) or Asana API | Free tier, well-documented |
| Scheduling | Simple cron / APScheduler | No need for heavier infra |
| Storage | SQLite | Enough for meeting/task history |
| UI | Streamlit | Fast to build, good for demos |

## 7. Build Plan: Condensed to 2 Cycles

### Cycle 1 (Weeks 1-2): Ship the MVP end-to-end
| Day range | Deliverable |
|---|---|
| Days 1-3 | Transcript ingestion + extraction prompt (JSON output), tested against 5-10 realistic sample transcripts |
| Days 4-6 | Owner resolution logic + ambiguity flagging |
| Days 7-9 | Notion/Asana integration, push confirmed tasks |
| Days 10-14 | Streamlit UI (upload → review → confirm → push), plus basic follow-up checker script that drafts nudges |

**Cycle 1 exit criteria:** you can feed in a real transcript and watch tasks appear in Notion/Asana with correct owners, and the system can flag one stale task with a drafted nudge. This is a fully demoable product.

### Cycle 2 (Weeks 3-4): Harden + one stretch feature
| Day range | Deliverable |
|---|---|
| Days 1-4 | Pick **one** stretch feature (recommend: audio input via Whisper, it's the most demo-impressive) |
| Days 5-7 | Edge case handling: crosstalk, no clear action items, malformed transcripts |
| Days 8-10 | README with architecture diagram, example runs, and an honest "known limitations" section |
| Days 11-14 | Buffer for polish, bug fixes, and recording a demo video/GIF |

## 8. Success Metrics (for your own evaluation, not vanity)

- Extraction precision on a held-out set of test transcripts (manually check: did it catch the real action items, did it avoid false positives?)
- Owner resolution accuracy
- End-to-end latency (transcript in → tasks pushed)
- Whether the follow-up checker correctly identifies stale tasks

## 9. Risks / Known Hard Parts

- **Ambiguous commitments in natural speech**, this is the core hard problem; budget real time for prompt iteration here, not just once.
- **API rate limits / auth setup** for Notion/Asana, test this early, not in week 4.
- **Over-scoping**, the biggest risk to finishing at all is trying to build audio + diarization + both tools + auto-send in one pass. The MVP/stretch split exists specifically to prevent this.

## 10. Interview Talking Points to Prepare

- Why you separated extraction from action (human-in-the-loop design)
- A specific failure case you hit and how you fixed it
- Why you chose structured JSON output over free-text parsing
- What you'd change for production scale (multi-tenant, auth, rate limiting)
