"""Live-mic transcription using faster-whisper (chunked near-real-time).

Design (see srujit/BRAINSTORM.md Section 10): we do NOT do word-by-word
streaming. We capture the mic in short chunks (~5s), transcribe each chunk on
the GPU, and append to a rolling transcript. Simpler, reliable, demos identically.

Layer 1 of the voice plan. Lazy imports so the rest of the app runs even
before audio deps / CUDA are installed.
"""
from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

from app.config import get_settings

_model = None  # cached WhisperModel


def _load_model(device: str, compute_type: str):
    """Build a WhisperModel and force lib loading so failures surface now.

    CUDA libraries (cuBLAS/cuDNN) load lazily on the first inference, not at
    construction — so we run a tiny warmup encode to trigger that load here,
    letting the caller fall back to CPU cleanly if the GPU stack is missing.
    """
    from faster_whisper import WhisperModel
    import numpy as np

    model = WhisperModel(get_settings().whisper_model, device=device, compute_type=compute_type)
    list(model.transcribe(np.zeros(16000, dtype="float32"))[0])  # warmup: forces lib load
    return model


def _get_model():
    global _model
    if _model is None:
        s = get_settings()
        try:
            _model = _load_model(s.whisper_device, s.whisper_compute_type)
        except Exception:
            # No CUDA / GPU stack -> fall back to CPU so the app still works.
            _model = _load_model("cpu", "int8")
    return _model


def preload_model() -> None:
    """Load the Whisper model now (downloads on first ever call) so the first
    live chunk transcribes immediately instead of after a slow cold start."""
    _get_model()


def transcribe_file(path: str) -> str:
    """Transcribe an existing audio file (used for tests / fallback path)."""
    segments, _ = _get_model().transcribe(path, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


def transcribe_bytes(data: bytes) -> str:
    """Transcribe raw audio bytes in-memory (no temp-file disk I/O).

    faster-whisper accepts a file-like object, so we decode straight from RAM —
    avoids a disk write+read on every ~5s live segment.
    """
    import io

    segments, _ = _get_model().transcribe(io.BytesIO(data), vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


class LiveTranscriber:
    """Capture mic audio in chunks and build a rolling transcript, live.

    Runs the mic capture + Whisper transcription in a background thread so the
    UI can poll ``live_text()`` and show words appearing as people speak.

    Usage:
        lt = LiveTranscriber()
        lt.start_live()
        ... lt.live_text() ...      # poll while speaking
        full_text = lt.stop()
    """

    def __init__(self, chunk_seconds: int = 5, samplerate: int = 16000,
                 on_text: Optional[Callable[[str], None]] = None,
                 device: Optional[int] = None):
        self.chunk_seconds = chunk_seconds
        self.samplerate = samplerate
        self.on_text = on_text
        self.device = device  # input device index; None = OS default
        self._capture_sr = samplerate
        self._audio_q: "queue.Queue" = queue.Queue()
        self._transcript: list[str] = []
        self._lock = threading.Lock()
        self._stop_evt = threading.Event()
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        # Observability so the UI can show whether audio is actually flowing.
        self._chunks = 0
        self._last_peak = 0.0
        self._seconds = 0.0
        self._error: Optional[str] = None

    def start(self) -> None:
        """Open the mic stream. Small 0.5s blocks flow into the queue; the
        worker accumulates them into ~chunk_seconds windows for Whisper."""
        import sounddevice as sd  # lazy import

        try:
            dev = sd.query_devices(self.device if self.device is not None else sd.default.device[0])
            self._capture_sr = int(dev["default_samplerate"])
        except Exception:
            self._capture_sr = self.samplerate

        def _callback(indata, frames, time_info, status):  # noqa: ANN001
            self._audio_q.put(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=self._capture_sr,
            blocksize=int(self._capture_sr * 0.5),  # 0.5s blocks -> responsive level meter
            dtype="int16", channels=1, callback=_callback,
            device=self.device,
        )
        self._stream.start()

    def _resample_16k(self, audio):
        import numpy as np

        sr = self._capture_sr
        if sr == self.samplerate or not audio.size:
            return audio
        n = int(round(audio.size * self.samplerate / sr))
        return np.interp(
            np.linspace(0, audio.size, n, endpoint=False),
            np.arange(audio.size), audio,
        ).astype("float32")

    def _transcribe_buffer(self, buf) -> None:
        segments, _ = _get_model().transcribe(buf, vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        self._chunks += 1
        if text:
            with self._lock:
                self._transcript.append(text)
            if self.on_text:
                self.on_text(text)

    def _worker(self) -> None:
        import numpy as np

        buf = np.empty(0, dtype="float32")
        target = self.samplerate * self.chunk_seconds  # samples at 16k
        try:
            while not self._stop_evt.is_set():
                try:
                    raw = self._audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                audio = np.frombuffer(raw, dtype=np.int16).astype("float32") / 32768.0
                self._last_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                self._seconds += audio.size / self._capture_sr
                buf = np.concatenate([buf, self._resample_16k(audio)])
                if buf.size >= target:
                    self._transcribe_buffer(buf)
                    buf = np.empty(0, dtype="float32")
            # Flush any remaining audio (so short recordings still transcribe).
            if buf.size >= self.samplerate:  # at least ~1s of speech
                self._transcribe_buffer(buf)
        except Exception as e:  # keep the thread from dying silently
            self._error = f"{type(e).__name__}: {e}"

    def start_live(self) -> None:
        """Start mic capture + a background transcription loop."""
        self._stop_evt.clear()
        self.start()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def live_text(self) -> str:
        """Current rolling transcript (safe to call from another thread)."""
        with self._lock:
            return " ".join(self._transcript).strip()

    def stats(self) -> dict:
        """Live counters so the UI can confirm audio is flowing."""
        return {
            "seconds": round(self._seconds, 1),
            "chunks": self._chunks,
            "peak": round(self._last_peak, 3),
            "error": self._error,
        }

    def stop(self) -> str:
        """Stop capture + worker (allowing a final flush), return the transcript."""
        self._stop_evt.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread is not None:
            self._thread.join(timeout=30)  # allow final-chunk transcription to finish
            self._thread = None
        return self.live_text()
