"""FastAPI smoke tests (offline). Verifies the app boots and routes are wired."""
from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import app
from app.schemas.models import ActionItem, MeetingExtraction, OwnerStatus

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_extract_endpoint_with_mocked_pipeline(monkeypatch):
    fake = MeetingExtraction(
        summary="s",
        action_items=[
            ActionItem(task="t", owner="Raj", owner_status=OwnerStatus.RESOLVED,
                       source_quote="q", confidence=0.9)
        ],
    )

    class FakePipeline:
        def invoke(self, state):
            return {"extraction": fake, "needs_review": False}

    monkeypatch.setattr(routes, "pipeline", FakePipeline())

    resp = client.post("/api/extract", json={"transcript": "hello", "known_owners": ["Raj"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is False
    assert body["extraction"]["action_items"][0]["owner"] == "Raj"


def test_ask_endpoint(monkeypatch):
    """Q&A over a transcript, without calling a real LLM."""
    import app.agents.qa as qa
    monkeypatch.setattr(qa, "answer_question", lambda t, q: "Raj owns the login bug.")

    resp = client.post("/api/ask", json={"transcript": "Raj will fix login.",
                                         "question": "Who owns the login bug?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": "Raj owns the login bug."}


def test_ask_empty_transcript_no_llm():
    """No transcript -> friendly guard message, no LLM call."""
    resp = client.post("/api/ask", json={"transcript": "  ", "question": "anything?"})
    assert resp.status_code == 200
    assert "start a meeting" in resp.json()["answer"].lower()


def test_extract_surfaces_extraction_error(monkeypatch):
    """A bad LLM response becomes a clean 502, not a raw 500 traceback."""
    from app.agents.extraction import ExtractionError

    class BoomPipeline:
        def invoke(self, state):
            raise ExtractionError("model returned garbage")

    monkeypatch.setattr(routes, "pipeline", BoomPipeline())
    resp = client.post("/api/extract", json={"transcript": "hello there friend"})
    assert resp.status_code == 502


def test_transcribe_endpoint(monkeypatch):
    """Voice upload -> transcript text, without loading a real Whisper model."""
    import app.stt.transcriber as transcriber
    monkeypatch.setattr(transcriber, "transcribe_bytes", lambda d: "hello from voice")

    resp = client.post(
        "/api/transcribe",
        files={"audio": ("clip.wav", b"RIFFfake", "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"transcript": "hello from voice"}


def test_confirm_pushes_and_persists(monkeypatch):
    """confirm() must push to Notion AND persist tasks locally for follow-up."""
    monkeypatch.setattr(routes, "push_confirmed_items", lambda items, label: ["pg1"])

    saved: list = []

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def add(self, obj):
            saved.append(obj)

        def flush(self):
            pass

        def commit(self):
            pass

    monkeypatch.setattr(routes, "SessionLocal", FakeSession)

    payload = {
        "items": [{"task": "ship it", "owner": "Raj", "owner_status": "resolved",
                   "source_quote": "q", "confidence": 0.9}],
        "meeting_label": "Standup",
    }
    resp = client.post("/api/confirm", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"pushed": 1, "notion_page_ids": ["pg1"]}
    # A Meeting row + a Task row should have been persisted.
    kinds = {type(o).__name__ for o in saved}
    assert "Task" in kinds and "Meeting" in kinds
