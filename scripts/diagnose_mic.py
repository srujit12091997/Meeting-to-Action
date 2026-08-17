"""Mic + Whisper diagnostic.

Run (uses the Windows default input device):
    .venv\\Scripts\\python.exe scripts\\diagnose_mic.py

Or target a specific device by its number from the list it prints:
    .venv\\Scripts\\python.exe scripts\\diagnose_mic.py 2

Isolates the three things that can break live transcription:
  1. Is a microphone available?
  2. Is audio actually being captured (non-silent)?
  3. Can Whisper transcribe it?
Speak for ~5 seconds when it says RECORDING.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd

DURATION = 5
TARGET_SR = 16000

print("=" * 60)
print("1) AUDIO DEVICES")
print("=" * 60)
device = int(sys.argv[1]) if len(sys.argv) > 1 else None
try:
    print(sd.query_devices())
    dev = sd.query_devices(device if device is not None else sd.default.device[0])
    native_sr = int(dev["default_samplerate"])
    picked = f"#{device}" if device is not None else "DEFAULT"
    print(f"\nUsing INPUT device ({picked}): {dev['name']}  (native samplerate {native_sr} Hz)")
    if "CABLE" in dev["name"] or "Virtual" in dev["name"]:
        print("   ⚠️  This is a VIRTUAL cable, not a physical mic. Pick a real one, e.g.:")
        print("       .venv\\Scripts\\python.exe scripts\\diagnose_mic.py 2   (Microphone Array)")
except Exception as e:
    print(f"!! Could not query devices: {e}")
    sys.exit(1)

print()
print("=" * 60)
print(f"2) RECORDING {DURATION}s at native {native_sr} Hz — SPEAK NOW…")
print("=" * 60)
try:
    audio = sd.rec(int(DURATION * native_sr), samplerate=native_sr, channels=1,
                   dtype="float32", device=device)
    sd.wait()
    audio = audio.flatten()
except Exception as e:
    print(f"!! Recording failed: {e}")
    sys.exit(1)

peak = float(np.max(np.abs(audio))) if audio.size else 0.0
print(f"Captured {audio.size} samples. Peak level = {peak:.4f}")
if peak < 0.01:
    print("!! Audio is essentially SILENT. Mic is muted, wrong device, or no OS permission.")
    print("   Windows: Settings > Privacy > Microphone must allow desktop apps.")
else:
    print("OK: real audio captured.")

# Resample to 16k for Whisper (simple linear resample).
if native_sr != TARGET_SR:
    n = int(round(audio.size * TARGET_SR / native_sr))
    audio16 = np.interp(np.linspace(0, audio.size, n, endpoint=False),
                        np.arange(audio.size), audio).astype("float32")
else:
    audio16 = audio

print()
print("=" * 60)
print("3) TRANSCRIBING with Whisper (first run downloads the model)…")
print("=" * 60)
try:
    from app.stt.transcriber import _get_model
    segments, _ = _get_model().transcribe(audio16, vad_filter=True)
    text = " ".join(s.text.strip() for s in segments).strip()
    print(f"TRANSCRIPT: {text!r}")
    print("\nRESULT:", "WORKS ✅" if text else "empty (spoke too quietly, or silence)")
except Exception as e:
    print(f"!! Whisper failed: {e}")
    sys.exit(1)
