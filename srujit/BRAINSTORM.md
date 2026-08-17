# Meeting-to-Action Agent: Brainstorm & Tracking Log

> **Purpose:** A living document to track our conversation, decisions, open questions, and
> progress so we build this project fast and don't lose context between sessions.
>
> **How to use it:** Every session we add to the Decision Log and Open Questions,
> tick off Progress items, and park loose ideas in the Parking Lot.

**Started:** 2026-08-09
**Companion doc:** [meeting-to-action-agent-prd.md](./meeting-to-action-agent-prd.md) (the PRD / source of truth for scope)

---

## 0. TL;DR of the Project
An AI agent that takes a meeting via **voice OR text** → extracts **decisions + action items (owner, deadline)** as structured JSON → lets a **human confirm** → **pushes tasks to Notion/Asana** → a scheduled checker **drafts nudges** for stale tasks. Portfolio project for AI Engineer roles (2026). Must be **demoable after Cycle 1**.

### ⭐ Product Purpose (user's own words: 2026-08-09)
> "The purpose is to **stay focused during meetings**. I want to just **speak naturally** and have the system handle notes and summary for me."

This reframes the project: it's not a transcript-parser, it's a **meeting co-pilot that frees the user from note-taking**. Implication: **voice input is core, not stretch.**

---

## 1. Decision Log
Decisions we've locked in. (Format: date, decision, rationale)

| Date | Decision | Rationale | Status |
|---|---|---|---|
| 2026-08-09 | Created this tracking doc | Keep context between sessions, move faster | ✅ Locked |
| 2026-08-09 | **Input = voice AND text** (not text-only) | Core purpose is speaking naturally / staying focused, voice is essential, not stretch | ✅ Locked |
| 2026-08-09 | **Voice capture = live mic (real-time)** | User wants to speak during the meeting and stay focused, the true vision, not post-meeting upload | ✅ Locked |
| 2026-08-09 | **STT engine = Whisper local** | Free, private, offline, strong interview talking point | ✅ Locked |
| 2026-08-09 | **Task tool = Notion** | User choice; PRD-recommended, free tier, good docs | ✅ Locked |
| 2026-08-09 | **LLM = Google Gemini (free tier)** | Zero cost; strong structured-JSON extraction | ✅ Locked |
| 2026-08-09 | **Whisper model = `small` via faster-whisper (int8)** | Best accuracy that fits 4 GB VRAM in real-time; see Section 11 | 🔶 Proposed |
| 2026-08-09 | **Full target stack locked** (LangGraph, FastAPI, Notion+Slack, SQLite→Supabase, Streamlit→Next.js, APScheduler→cloud cron, Langfuse/LangSmith) | User-specified production-grade architecture; see Section 12 | ✅ Locked |
| 2026-08-09 | **Build MVP tier first, prod swaps later** | Honors target stack while avoiding over-scoping; SQLite/Streamlit/APScheduler/local now, Postgres/Next.js/cloud-cron later | ✅ Locked |
| 2026-08-09 | Project scaffold created (`app/`, `frontend/`, `tests/`) | Concrete home for code; MVP-first structure | ✅ Locked |

---

## 2. Open Questions (need answers to move fast)
Things we must resolve. Highest-impact at top.

- [x] ~~**Voice capture mode:**~~ → **Live mic (real-time)** ✅
- [x] ~~**Speech-to-text engine:**~~ → **Whisper local** ✅
- [x] ~~**Hardware check**~~ → RTX 3050 Laptop (4 GB VRAM), Ryzen 7 6000, Python 3.11.5, CUDA 13.2 driver ✅ (see Section 11)
- [x] ~~**Whisper model size**~~ → **`small` via faster-whisper (int8)** proposed ✅
- [x] ~~**Real-time approach**~~ → **chunked near-real-time** (see Section 10 layers) ✅
- [x] ~~**Task tool**~~ → **Notion** ✅
- [x] ~~**LLM provider**~~ → **Google Gemini (free tier)** ✅
- [ ] **API keys:** Do you have (a) a Google Gemini API key and (b) a Notion integration token yet? Needed before Days 7-9.
- [ ] **CUDA/PyTorch install:** Need to install a CUDA-enabled PyTorch or faster-whisper build to actually use the GPU (see Section 11).
- [ ] **Owner resolution:** Where does the list of team members come from? (hardcoded roster? config file? inferred from transcript?)
- [ ] **"Stale" definition:** What makes a task stale, no status change after N days? What's N?
- [ ] **Sample transcripts:** Do we have real ones, or do we generate synthetic ones for testing?
- [ ] **Deployment:** Local-only demo, or hosted (Streamlit Cloud)?
- [ ] **Dev environment:** Python version installed? Virtualenv/conda preference?

---

## 3. Risks & Watch-outs (from PRD + our discussion)
- ⚠️ **Ambiguous speech** ("I'll look into it"), the core hard problem. Budget prompt-iteration time.
- ⚠️ **API auth / rate limits** (Notion/Asana), test integration EARLY, not in week 4.
- ⚠️ **Over-scoping**, do NOT build audio + diarization + both tools + auto-send in one pass. MVP first.

---

## 4. Progress Tracker (Cycle 1 = MVP)
Mirrors PRD Section 7. Tick as we complete.

### Cycle 1: Ship MVP end-to-end ✅ DONE (2026-08-15)
- [x] **Days 1-3:** Transcript ingestion + extraction → JSON. ✅ Validated live via **Google Gemini free tier**.
- [x] **Days 4-6:** Owner resolution logic + ambiguity flagging, ✅ **DONE & TESTED** (owners flagged, never guessed; AMBIGUOUS on collective "we").
- [x] **Days 7-9:** Notion integration, ✅ real tasks pushed live to the Notion DB.
- [x] **Days 10-14:** Streamlit UI + follow-up checker, ✅ end-to-end proven; `confirm()` now persists Tasks to the DB so the stale-check sees real data.

**Env status:** clean `.venv` (Python 3.11.5); Gemini provider added (`google-genai`). 9/9 offline tests pass. Full chain run: transcript → extract → Notion → stale-task nudge drafted.

**Cycle 1 exit criteria:** ✅ Met, fed a real transcript, tasks landed in Notion with correct owners, and the checker flagged a stale task with a drafted nudge.

### Cycle 2: Harden + one stretch feature (IN PROGRESS)
- [x] Edge cases validated: crosstalk, no-actions (0 hallucinated tasks), collective-owner → AMBIGUOUS, client call, 1:1. All 4 hard transcripts pass.
- [x] **Stretch feature = Whisper voice input, WORKING.** `faster-whisper` (no torch; CTranslate2), GPU→CPU auto-fallback, `/api/transcribe` endpoint, Streamlit `st.audio_input` recorder. Validated end-to-end: SAPI-synthesized speech → exact transcript → 2 tasks with resolved owners + deadlines. 10/10 tests pass.
- [~] Live-mic chunked path, **now wired into the UI**: `LiveTranscriber` runs a background thread (mic → ~5s chunks → Whisper → rolling transcript); Streamlit "🔴 Start live mic" button auto-refreshes the live transcript every 2s. Code + import checks pass; **needs a real-mic run on user's machine to confirm** (no mic in dev env).
- [x] **Malformed / empty / non-meeting transcript handling + tests.** Empty/whitespace/too-short → guarded empty result (no LLM call); bad LLM output → `ExtractionError` → API 502; gibberish → 0 tasks, no hallucination. Added `test_extraction_hardening.py` + `malformed_example.txt`. **16/16 tests pass.**
- [ ] README + architecture diagram + known limitations
- [ ] Buffer + demo video/GIF

---

## 5. Architecture Snapshot (updated for voice+text)
```
Voice (mic / audio file)          Text (paste / upload)
        │                                  │
        └──────────► Speech-to-Text ◄──────┘   (Whisper or cloud STT; text path skips this)
                          │
                    Transcript (text)
                          │
              Extraction Agent (LLM, structured JSON)
                          │
              Owner Resolution (name-match + ambiguity flag)
                          │
              Review UI (human confirms before any external write)
                          │
              Task Sync (Notion/Asana API)
                          │
              Follow-up Checker (scheduled) → drafts nudge for stale tasks
```
**Design principle:** human confirms before ANY external write (push tasks / send nudges).
**New:** voice and text both funnel into the same transcript, so everything downstream is unchanged, the only new component is the STT front-end.

---

## 10. Voice Input: The Big Fork (decide this first)
Because voice is now core, HOW we capture it drives the whole build. Two paths:

| | **A) Upload audio file (post-meeting)** | **B) Live mic (real-time during meeting)** |
|---|---|---|
| Effort | Low, matches PRD's staged plan | High, streaming audio, live transcription, UI complexity |
| Fits "stay focused" purpose? | Partly (you still record separately) | Fully (this is the real vision) |
| Demo impressiveness | Good | Excellent |
| MVP-friendly? | ✅ Yes | ⚠️ Risky for MVP |
| Tech | Whisper on a saved .wav/.mp3 | Streaming STT + mic capture (sounddevice/WebRTC) |

**✅ DECISION (2026-08-09):** User chose **B, Live mic (real-time)** with **Whisper local**. This is the true vision (speak naturally, stay focused).

### How we de-risk live mic (so we don't fall into the over-scoping trap)
Live mic is the hard path. We make it safe by building it in layers, each layer is independently demoable:

1. **Layer 1, Mic → text (chunked):** Capture mic audio, transcribe in short chunks (~5-10s) with Whisper, print rolling transcript. *Not* true streaming yet, "near real-time." This is 90% of the value for 20% of the effort.
2. **Layer 2, Full transcript → extraction:** Once the meeting ends, feed the accumulated transcript into the existing LLM extraction pipeline. (Downstream is unchanged.)
3. **Layer 3, Polish:** Reduce chunk latency, handle silence/pauses, live on-screen transcript in Streamlit.

> **Key insight:** "Real-time" for a note-taker doesn't need word-by-word streaming. **Chunked near-real-time (transcribe every few seconds) is simpler, more reliable, and looks identical in a demo.** We start there; true streaming is an optional later upgrade.

---

## 6. Data Contract (draft: the JSON the LLM should output)
> We'll refine this in Days 1-3. First-pass strawman:
```json
{
  "meeting_title": "string",
  "meeting_date": "YYYY-MM-DD",
  "decisions": ["string"],
  "action_items": [
    {
      "task": "string",
      "owner": "string | null",
      "owner_ambiguous": true,
      "deadline": "YYYY-MM-DD | null",
      "source_quote": "string"
    }
  ]
}
```
_Open: do we want a confidence score per item? A `priority` field?_

---

## 11. Environment & Hardware (detected 2026-08-09)
| Component | Detected | Notes |
|---|---|---|
| GPU | **NVIDIA RTX 3050 Laptop, 4 GB VRAM** | CUDA-capable. 4 GB is the key constraint on Whisper model size. |
| CUDA driver | **13.2** (driver 596.08) | Driver ready; still need CUDA-enabled PyTorch/faster-whisper in the venv. |
| CPU | **AMD Ryzen 7 6000 series** | Good fallback if GPU is busy. |
| Python | **3.11.5** (Anaconda) | Fine for all our libs. |
| pip | 24.0 | ⚠️ Note: pip reports python 3.12 while `python` is 3.11.5 → Anaconda base vs another env mismatch. **We'll create a clean dedicated venv to avoid confusion.** |

### Whisper model choice: reasoning for 4 GB VRAM
| Model | Approx VRAM (faster-whisper int8) | Real-time on RTX 3050? | Accuracy |
|---|---|---|---|
| tiny | ~0.5 GB | ✅ Very fast | Low |
| base | ~0.7 GB | ✅ Fast | OK |
| **small** ⭐ | **~1-2 GB** | **✅ Comfortable** | **Good, our pick** |
| medium | ~2.5-3 GB | ⚠️ Tight, slower | Better |
| large-v3 | ~4.5 GB+ | ❌ Won't fit | Best |

**Decision: `small` model via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) with int8 quantization.**
- `faster-whisper` (CTranslate2) is ~4x faster and lighter than vanilla `openai-whisper`, the difference between "real-time" and "not" on a 4 GB laptop GPU.
- `small` is the sweet spot: solid accuracy, fits VRAM with headroom, keeps chunk latency low.
- We can bump to `medium` later if accuracy needs it and latency allows.

### Env setup plan (before coding)
1. Create a clean venv (avoid the 3.11-vs-3.12 pip mismatch above).
2. Install: `faster-whisper`, `sounddevice` (mic capture), `google-genai` (Gemini LLM), `notion-client`, `streamlit`, `APScheduler`.
3. Install CUDA-enabled runtime for faster-whisper and smoke-test GPU transcription.

---

## 12. Finalized Tech Stack (2026-08-09)
User-specified, production-grade. We build the **MVP tier now**, and the structure is designed so the **prod swap** is a clean drop-in later.

| Layer | MVP tier (build now) | Production path (later) | Notes |
|---|---|---|---|
| LLM / reasoning | **Google Gemini (free tier)**, structured JSON | same | Core extraction brain (see Session 3: switched to Gemini for zero cost) |
| Agent orchestration | **LangGraph** | same | Stateful graph: extract → resolve owners → review → sync → follow-up |
| Backend | **Python + FastAPI** | same | REST API; Streamlit + future Next.js both call it |
| Task integration | **Notion API** | + refinements | Push confirmed tasks |
| Messaging | **Slack API** | same | Draft/send follow-up nudges |
| Database | **SQLite** | **Postgres via Supabase** | SQLAlchemy so the swap is a URL change |
| Frontend | **Streamlit** | **Next.js + Tailwind** | Streamlit talks to FastAPI, so backend is UI-agnostic |
| Scheduling | **APScheduler** (local) | **cron on Railway/Render/Fly.io** | Same follow-up job, different trigger |
| Observability | **Langfuse or LangSmith** | same | Trace LLM calls, latency, token cost |
| STT | **faster-whisper `small`**, live mic | same | See Section 11 |

**Architecture principle:** FastAPI is the single backend brain; STT, LLM, DB, and integrations are modules behind it. Streamlit (and later Next.js) are thin clients. This keeps every "MVP → prod" swap isolated to one module.

**Decision, Langfuse vs LangSmith:** _lean Langfuse_ (open-source, self-hostable, generous free tier, cleaner fit with a non-LangChain-heavy stack). ⬜ Confirm with user.

---

## 7. Parking Lot (ideas we don't act on yet)
- Confidence score per extracted action item
- Slack/email auto-send (stretch)
- Weekly digest email (stretch)
- Multi-meeting analytics dashboard (stretch)
- Speaker diarization (stretch)

---

## 8. Session Notes
Running log of what we discussed each session.

### Session 3: 2026-08-15 (Cycle 1 shipped + Cycle 2 kickoff)
- **Cost decision:** user wants zero spend → extraction runs on the **Google Gemini free tier** (`google-genai`, `gemini-flash-latest`; `gemini-2.5-flash` was 404 for new keys).
- **Cycle 1 closed end-to-end:** live extraction → 3 tasks pushed to Notion → follow-up checker drafted a stale-task nudge.
- **Fixed wiring gap:** `confirm()` pushed to Notion but never saved Task rows, so the DB-backed stale-check saw nothing. `confirm()` now persists Meeting + Task rows (with `notion_page_id`). Added `test_confirm_pushes_and_persists`. **9/9 tests pass.**
- **Cycle 2 started, edge cases validated:** ran all 4 hard transcripts. No-actions → 0 tasks (no hallucination); crosstalk → clean tasks + deferred ownership; client call → collective "we" flagged AMBIGUOUS; 1:1 → correct attribution.
- **Open decision:** which Cycle 2 stretch feature to build (Whisper live-mic vs. lighter options).
- **Autonomous loop closed:** enabled the APScheduler follow-up in `app/main.py` (was commented out). New `run_stale_check` logs drafted nudges; `start_scheduler(run_now=True)` fires one check on startup then daily. Verified live, the background job fired, found the stale task, and drafted a nudge. **Never auto-sends** (human reviews via `GET /api/followups`). Cleaned test-artifact rows from the DB; added `test_scheduler.py`. **18/18 tests pass.**

### Session 2: 2026-08-09 (Cycle 1 build)
- Created clean `.venv` (Python 3.11.5); installed core deps (deferred Whisper/torch to voice layer).
- Added 4 more sample transcripts (client call, crosstalk, 1:1, no-actions) → **5 total** covering hard cases.
- **Days 4-6 DONE:** owner resolution + ambiguity flagging implemented and covered by 5 unit tests.
- Built `scripts/run_extraction.py` (Days 1-3 iteration harness) and `tests/test_pipeline_offline.py` + `tests/test_api.py`.
- **8/8 offline tests pass.** FastAPI boots; `/health` and `/api/extract` verified with mocked LLM.
- **Blocked on user:** fill `.env` (Gemini key) + finish `NOTION_SETUP.md`, then run real extraction + `test_notion.py`.

### Session 1: 2026-08-09
- Read the PRD together; understood the project end-to-end.
- Created this brainstorming/tracking doc.
- **User clarified purpose:** stay focused in meetings, speak naturally, system handles notes + summary.
- **Scope change locked:** input is **voice AND text** (voice promoted from stretch → core).
- Added Section 10 (Voice Input fork) + updated architecture with an STT front-end.
- **Decisions locked:** voice capture = **live mic (real-time)**; STT = **Whisper local**.
- Agreed de-risking plan: build live mic in **layers** (chunked near-real-time first). See Section 10.
- **Hardware detected:** RTX 3050 Laptop (4 GB VRAM), Ryzen 7 6000, Python 3.11.5, CUDA 13.2 driver.
- **Decisions locked:** Task tool = **Notion**; LLM = **Google Gemini (free tier)**. Whisper model = **`small` (faster-whisper int8)** proposed.
- Noted a pip/python version mismatch → will use a clean dedicated venv.
- **Next:** confirm API keys (Gemini + Notion), then set up env and start Days 1-3 (extraction prompt + JSON contract).
- **Full target stack locked** (Section 12): LangGraph + FastAPI + Notion/Slack + SQLite→Supabase + Streamlit→Next.js + APScheduler→cloud cron + Langfuse.
- **Project scaffolded**, `app/` (config, schemas, agents, graph, integrations, db, stt, scheduler, api), `frontend/streamlit_app.py`, `scripts/test_notion.py`, `tests/sample_transcripts/`, `requirements.txt`, `.gitignore`, `.env.example`, `README.md`. All files compile clean.
- **Next:** user creates venv + `pip install -r requirements.txt`, fills `.env`, runs `NOTION_SETUP.md`, then `python scripts/test_notion.py`. Then we implement the real extraction test loop (Days 1-3).

---

## 9. Next Actions (what to do right now)
1. **User:** create clean venv → `pip install -r requirements.txt`.
2. **User:** generate Google Gemini API key + finish `srujit/NOTION_SETUP.md`; fill `.env`.
3. **Verify plumbing:** `python scripts/test_notion.py` (creates one test task in Notion).
4. **Then together:** run extraction on `tests/sample_transcripts/standup_example.txt`, iterate the prompt, confirm the JSON contract holds (Days 1-3).
5. **After that:** wire the live-mic Layer 1 (mic → chunked Whisper → transcript).
