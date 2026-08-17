"""Streamlit dashboard: live meeting → transcript + action items + ask-the-agent
→ review → push to Notion. Thin client over the FastAPI backend.

Run (after `uvicorn app.main:app`):  streamlit run frontend/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Meeting-to-Action Agent", page_icon="📝", layout="wide")

st.markdown(
    """
    <style>
      #MainMenu, footer {visibility: hidden;}
      .block-container {padding-top: 1.2rem; max-width: 1200px;}
      div.stButton > button {border-radius: 10px; font-weight: 600;}
      div.stButton > button[kind="primary"] {box-shadow: 0 4px 14px rgba(99,102,241,.35);}
      [data-testid="stMetric"] {background:#F8FAFC; border:1px solid #E2E8F0;
        border-radius:12px; padding:.5rem .9rem;}
      .brand {font-size:1.25rem; font-weight:800; color:#4F46E5; padding-top:.35rem;}
      .hdrbar {border-bottom:1px solid #E5E7EB; padding-bottom:.7rem; margin-bottom:1rem;}
      .pill {display:inline-block; padding:.12rem .55rem; border-radius:999px;
             font-size:.75rem; font-weight:600;}
      .pill-ok  {background:#DCFCE7; color:#166534;}
      .pill-flag{background:#FEE2E2; color:#991B1B;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("page", "Dashboard")
st.session_state.setdefault("chat", [])


# --------------------------------------------------------------- helpers -----
@st.cache_data
def _input_devices() -> list[tuple[int, str]]:
    import sounddevice as sd

    return [
        (i, f"{i}: {d['name']}")
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] > 0
    ]


def _summary_markdown(ext: dict) -> str:
    head = " · ".join(x for x in [ext.get("meeting_title"), ext.get("meeting_date")] if x)
    lines = ["# Meeting Summary"] + ([f"_{head}_"] if head else [])
    lines += ["", "## Overview", ext.get("summary", "") or "(none)"]
    lines += ["", "## Key Decisions"] + ([f"- {d}" for d in ext.get("decisions", [])] or ["- (none)"])
    lines += ["", "## Proposed Solutions"] + (
        [f"- {s}" for s in ext.get("proposed_solutions", [])] or ["- (none)"]
    )
    lines += ["", "## Next Action Steps"]
    if ext.get("action_items"):
        for it in ext["action_items"]:
            lines.append(f"- {it['task']} — {it.get('owner') or 'Unassigned'} "
                         f"(due {it.get('deadline') or 'no deadline'})")
    else:
        lines.append("- (none)")
    if ext.get("open_questions"):
        lines += ["", "## Open Questions"] + [f"- {q}" for q in ext["open_questions"]]
    return "\n".join(lines)


def _summary_html(ext: dict) -> str:
    """HTML body for the summary email."""
    def _ul(items):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items else "<p><i>None</i></p>"

    acts = "<p><i>None</i></p>"
    if ext.get("action_items"):
        rows = "".join(
            f"<li><b>{it['task']}</b> — {it.get('owner') or 'Unassigned'} "
            f"(due {it.get('deadline') or 'no deadline'})</li>"
            for it in ext["action_items"]
        )
        acts = f"<ul>{rows}</ul>"
    head = " · ".join(x for x in [ext.get("meeting_title"), ext.get("meeting_date")] if x)
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:640px">
      <h2 style="color:#4F46E5">📝 Meeting Summary</h2>
      {f'<p style="color:#666">{head}</p>' if head else ''}
      <h3>Overview</h3><p>{ext.get('summary','') or 'No summary.'}</p>
      <h3>✅ Key Decisions</h3>{_ul(ext.get('decisions', []))}
      <h3>💡 Proposed Solutions</h3>{_ul(ext.get('proposed_solutions', []))}
      <h3>📌 Next Action Steps</h3>{acts}
      {f"<h3>❓ Open Questions</h3>{_ul(ext.get('open_questions', []))}" if ext.get('open_questions') else ''}
      <hr><p style="color:#999;font-size:12px">Sent by Meeting-to-Action Agent</p>
    </div>"""


def _gcal_link(it: dict, meeting_title: str | None) -> str:
    """A Google Calendar 'add event' link for one dated task."""
    due = date.fromisoformat(it["deadline"])
    params = {
        "action": "TEMPLATE",
        "text": f"{it.get('task', 'Task')} — {it.get('owner') or 'Unassigned'}",
        "dates": f"{due.strftime('%Y%m%d')}/{(due + timedelta(days=1)).strftime('%Y%m%d')}",
        "details": f"Action item from: {meeting_title or 'Meeting'}",
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)


def render_share(ext: dict) -> None:
    """Post-meeting actions: email the summary + add tasks to a calendar."""
    st.subheader("🚀 Share & schedule")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📧 Email the summary**")
        to = st.text_input("Recipients (comma-separated)", key="email_to",
                           placeholder="alice@team.com, bob@team.com")
        if st.button("📧 Send summary email"):
            recips = [r.strip() for r in to.replace("\n", ",").split(",") if r.strip()]
            if not recips:
                st.warning("Add at least one recipient.")
            else:
                try:
                    r = requests.post(f"{API}/api/email-summary", json={
                        "recipients": recips,
                        "subject": f"Meeting Summary — {ext.get('meeting_title') or 'Meeting'}",
                        "html": _summary_html(ext),
                    }, timeout=60)
                    if r.status_code == 400:
                        st.error(r.json()["detail"])  # SMTP not configured
                    else:
                        r.raise_for_status()
                        st.success(f"📨 Sent to {r.json()['sent']} recipient(s).")
                except Exception as e:
                    st.error(f"Couldn't send: {e}")

    with col2:
        st.markdown("**📅 Add tasks to calendar**")
        dated = [it for it in ext.get("action_items", []) if it.get("deadline")]
        if not dated:
            st.caption("No tasks have deadlines yet — add deadlines to schedule reminders.")
        else:
            if st.button("📅 Generate calendar file (.ics)"):
                r = requests.post(f"{API}/api/calendar-ics", json={
                    "action_items": ext.get("action_items", []),
                    "meeting_title": ext.get("meeting_title"),
                }, timeout=60)
                r.raise_for_status()
                st.session_state["ics"] = r.json()["ics"]
            if st.session_state.get("ics"):
                st.download_button("⬇️ Download .ics (with reminders)", st.session_state["ics"],
                                   file_name="meeting_tasks.ics", mime="text/calendar")
            st.caption("Or one-click add to Google Calendar:")
            for it in dated:
                st.markdown(f"- [📅 {it['task']}]({_gcal_link(it, ext.get('meeting_title'))})")


def _extract_payload(transcript: str) -> dict:
    return {
        "transcript": transcript,
        "meeting_title": st.session_state.get("title") or None,
        "meeting_date": st.session_state.get("m_date") or None,
        "known_owners": [r.strip() for r in st.session_state.get("roster", []) if r.strip()],
    }


# --------------------------------------------------------------- sidebar -----
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state["m_date"] = st.text_input("Meeting date (YYYY-MM-DD)", "")
    st.session_state["roster"] = st.text_area(
        "Known team members", "", placeholder="Sarah\nRaj\nPriya",
        help="Matching owners show ✅ resolved instead of 🚩 flagged.",
    ).splitlines()
    devices = _input_devices()
    default_idx = next(
        (n for n, (_, label) in enumerate(devices)
         if "microphone" in label.lower() and "cable" not in label.lower()), 0,
    )
    picked = st.selectbox(
        "Microphone", devices, index=default_idx, format_func=lambda t: t[1],
        disabled=st.session_state.get("live") is not None,
    )
    st.divider()
    st.caption(f"Backend: {API}")


# ---------------------------------------------------------------- header -----
h = st.columns([1.1, 1, 1, 2.4, 1.3, 1.9])
h[0].markdown('<div class="brand">📝 M2A</div>', unsafe_allow_html=True)
if h[1].button("📊 Dashboard", use_container_width=True,
               type="primary" if st.session_state["page"] == "Dashboard" else "secondary"):
    st.session_state["page"] = "Dashboard"
    st.rerun()
if h[2].button("🕘 History", use_container_width=True,
               type="primary" if st.session_state["page"] == "History" else "secondary"):
    st.session_state["page"] = "History"
    st.rerun()
st.session_state["title"] = h[3].text_input(
    "title", value=st.session_state.get("title", ""), placeholder="Team standup",
    label_visibility="collapsed",
)
with h[4].popover("📁 Upload audio", use_container_width=True):
    up = st.audio_input("Record / upload a clip")
    if up is not None and st.button("Transcribe"):
        with st.spinner("Transcribing…"):
            r = requests.post(f"{API}/api/transcribe",
                              files={"audio": ("rec.wav", up.getvalue(), "audio/wav")}, timeout=300)
        r.raise_for_status()
        st.session_state["transcript_text"] = r.json()["transcript"]
        st.session_state.pop("extraction", None)
        st.success("Transcribed.")

recording = st.session_state.get("live") is not None
if not recording:
    if h[5].button("▶ Start live meeting", type="primary", use_container_width=True):
        from app.stt.transcriber import LiveTranscriber, preload_model

        with st.spinner("Loading Whisper (first time downloads the model)…"):
            preload_model()
        lt = LiveTranscriber(device=picked[0])
        lt.start_live()
        st.session_state["live"] = lt
        st.session_state["chat"] = []
        st.session_state.pop("extraction", None)
        st.session_state.pop("live_extraction", None)
        st.rerun()
else:
    if h[5].button("⏹ Stop meeting", type="primary", use_container_width=True):
        with st.spinner("Finishing transcription…"):
            st.session_state["transcript_text"] = st.session_state["live"].stop()
        if st.session_state.get("live_extraction"):
            st.session_state["extraction"] = st.session_state["live_extraction"]
        st.session_state["live"] = None
        st.session_state.pop("last_live_extract", None)
        st.rerun()
st.markdown('<div class="hdrbar"></div>', unsafe_allow_html=True)


# ------------------------------------------------------------- results -------
def render_results(ext: dict) -> None:
    st.subheader("📄 Meeting summary")
    left, right = st.columns([3, 2])
    with left:
        with st.container(border=True):
            st.markdown("#### Overview")
            st.write(ext.get("summary", "") or "_No summary captured._")
        with st.container(border=True):
            st.markdown("#### ✅ Key Decisions")
            for d in ext.get("decisions", []) or []:
                st.markdown(f"- {d}")
            if not ext.get("decisions"):
                st.caption("None recorded.")
        with st.container(border=True):
            st.markdown("#### 💡 Proposed Solutions")
            for s in ext.get("proposed_solutions", []) or []:
                st.markdown(f"- {s}")
            if not ext.get("proposed_solutions"):
                st.caption("None recorded.")
    with right:
        if ext.get("open_questions"):
            with st.container(border=True):
                st.markdown("#### ❓ Open Questions")
                for q in ext["open_questions"]:
                    st.markdown(f"- {q}")
        st.download_button("⬇️ Download summary (.md)", _summary_markdown(ext),
                           file_name="meeting_summary.md", mime="text/markdown")

    st.divider()
    render_share(ext)

    st.divider()
    st.subheader("Confirm & push to Notion")
    st.info("⚠️ Ambiguous/unresolved owners are flagged. Edit anything, then push.")
    for i, item in enumerate(ext.get("action_items", [])):
        resolved = item["owner_status"] == "resolved"
        with st.expander(item["task"], expanded=not resolved):
            pill = ('<span class="pill pill-ok">resolved</span>' if resolved
                    else '<span class="pill pill-flag">review</span>')
            st.markdown(f"Status {pill}", unsafe_allow_html=True)
            item["task"] = st.text_input("Task", item["task"], key=f"t{i}")
            item["owner"] = st.text_input("Owner", item.get("owner") or "", key=f"o{i}")
            item["deadline"] = st.text_input("Deadline", item.get("deadline") or "", key=f"d{i}")
            st.caption(f"Source: “{item['source_quote']}”")
    if st.button("✅ Confirm & push to Notion", type="primary"):
        with st.spinner("Pushing…"):
            r = requests.post(f"{API}/api/confirm",
                              json={"items": ext["action_items"],
                                    "meeting_label": st.session_state.get("title") or "meeting"},
                              timeout=120)
        r.raise_for_status()
        st.success(f"🎉 Pushed {r.json()['pushed']} tasks to Notion.")
        st.balloons()


# ------------------------------------------------------------- dashboard -----
def render_dashboard() -> None:
    recording = st.session_state.get("live") is not None
    live_ext = st.session_state.get("live_extraction") if recording else st.session_state.get("extraction")
    items = (live_ext or {}).get("action_items", []) if live_ext else []

    left, right = st.columns([2, 1])
    with left:
        st.markdown("### 🎙️ Live Transcript")
        if recording:
            lt = st.session_state["live"]
            stats = lt.stats()
            c1, c2, c3 = st.columns(3)
            c1.metric("Captured", f"{stats['seconds']}s")
            c2.metric("Mic level", stats["peak"])
            c3.metric("Chunks", stats["chunks"])
            if stats["peak"] == 0.0 and stats["seconds"] > 1:
                st.warning("Mic level 0 — wrong device or muted (pick another mic in ⚙️).")
            st.text_area("t", lt.live_text(), height=300, disabled=True, label_visibility="collapsed")
            st.caption("🧠 Understanding the conversation and breaking it into tasks…")
        else:
            st.text_area("t", value=st.session_state.get("transcript_text", ""), height=300,
                         placeholder="Press ▶ Start live meeting, or 📁 Upload audio.",
                         label_visibility="collapsed", key="transcript_box")
    with right:
        st.markdown(f"### 📌 Action Items ({len(items)})")
        with st.container(border=True, height=360):
            if items:
                for it in items:
                    owner = it.get("owner") or "🚩 Unassigned"
                    due = it.get("deadline") or "no deadline"
                    st.markdown(f"**{it['task']}**  \n{owner} · due *{due}*")
                    st.divider()
            else:
                st.caption("0 so far. Assign tasks like “**Sarah** will finalize the budget **by Friday**.”")

    # ------- Ask the agent -------
    st.markdown("### 💬 Ask the agent")
    qa_transcript = (st.session_state["live"].live_text() if recording
                     else st.session_state.get("transcript_text", ""))
    if recording:
        st.text_input("ask", placeholder="Recording… stop the meeting to ask questions.",
                      disabled=True, label_visibility="collapsed")
    elif qa_transcript.strip():
        with st.form("ask_form", clear_on_submit=True):
            q = st.text_input("ask", placeholder="Ask anything about the meeting…",
                              label_visibility="collapsed")
            if st.form_submit_button("Ask") and q.strip():
                try:
                    with st.spinner("Thinking…"):
                        r = requests.post(f"{API}/api/ask",
                                          json={"transcript": qa_transcript, "question": q}, timeout=120)
                    r.raise_for_status()
                    answer = r.json()["answer"]
                except Exception:
                    answer = "⚠️ The model is briefly busy (rate limit). Please ask again."
                st.session_state["chat"].append(("user", q))
                st.session_state["chat"].append(("assistant", answer))
        for role, msg in st.session_state["chat"]:
            st.chat_message(role).write(msg)
    else:
        st.text_input("ask", placeholder="Start a meeting first to ask questions.",
                      disabled=True, label_visibility="collapsed")

    # ------- results (summary + push) after the meeting -------
    if not recording and st.session_state.get("extraction"):
        st.divider()
        render_results(st.session_state["extraction"])

    # ------- live refresh loop -------
    if recording:
        EXTRACT_EVERY = 15
        text = st.session_state["live"].live_text()
        now = time.time()
        if text and now - st.session_state.get("last_live_extract", 0) >= EXTRACT_EVERY:
            try:
                r = requests.post(f"{API}/api/extract", json=_extract_payload(text), timeout=60)
                if r.ok:
                    st.session_state["live_extraction"] = r.json()["extraction"]
            except Exception:
                pass
            st.session_state["last_live_extract"] = now
        time.sleep(2)
        st.rerun()


# --------------------------------------------------------------- history -----
def render_history() -> None:
    st.markdown("### 🕘 Meeting history")
    try:
        r = requests.get(f"{API}/api/history", timeout=30)
        r.raise_for_status()
        tasks = r.json()["tasks"]
    except Exception as e:
        st.error(f"Couldn't load history: {e}")
        return
    if not tasks:
        st.info("No tasks yet. Run a meeting and push to Notion.")
        return
    st.dataframe(
        [{"Task": t["task"], "Owner": t["owner"] or "—", "Deadline": t["deadline"] or "—",
          "Status": t["status"], "Meeting": t["meeting"] or "—", "Created": t["created_at"][:10]}
         for t in tasks],
        use_container_width=True, hide_index=True,
    )


# ----------------------------------------------------------------- route -----
if st.session_state["page"] == "History":
    render_history()
else:
    render_dashboard()
