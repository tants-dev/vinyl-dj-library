"""Tests for enrich/audio_analysis.py.

These tests exercise the real librosa code. The synthetic audio signals
used here are short (≤5s) so the test suite stays fast, and assertions
are intentionally loose — we care about shape and range, not that
librosa gets the exact key right for an artificial sine wave.
"""

import math
import struct
import tempfile
import wave
from unittest.mock import patch

import numpy as np
import pytest

from enrich.audio_analysis import _detect_key, analyze_sample
from enrich.sources.base import Match


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_sine_wav(path: str, freq_hz: float = 261.63, duration: float = 3.0, sr: int = 22050):
    """Write a pure sine wave at freq_hz to path as a mono 16-bit PCM WAV."""
    n = int(duration * sr)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        data = struct.pack(
            f"<{n}h",
            *(int(32767 * math.sin(2 * math.pi * freq_hz * i / sr)) for i in range(n)),
        )
        wf.writeframes(data)


def _write_kick_pattern_wav(path: str, bpm: float = 120.0, bars: int = 8, sr: int = 22050):
    """Write a simple kick-on-every-beat pattern so beat_track has something to find."""
    beat_samples = int(sr * 60.0 / bpm)
    n_beats = bars * 4
    n_samples = beat_samples * n_beats
    y = np.zeros(n_samples, dtype=np.float32)
    for b in range(n_beats):
        start = b * beat_samples
        # Short 50ms click to mark the beat
        click_len = int(0.05 * sr)
        t = np.linspace(0, 1, click_len)
        y[start : start + click_len] += np.sin(2 * np.pi * 80 * t) * np.exp(-30 * t)
    # Normalise
    y = y / (np.abs(y).max() + 1e-9)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        data = struct.pack(f"<{n_samples}h", *(int(s * 32767) for s in y))
        wf.writeframes(data)


# ── _detect_key() ─────────────────────────────────────────────────────────────

def test_detect_key_returns_key_string_and_confidence():
    """_detect_key always returns (str, float) regardless of signal quality."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, freq_hz=261.63, duration=3.0)
        tmp_path = f.name

    import librosa
    y, sr = librosa.load(tmp_path, sr=22050, mono=True)
    key, confidence = _detect_key(y, sr)

    assert isinstance(key, str)
    assert "major" in key or "minor" in key
    assert 0.0 <= confidence <= 1.0


def test_detect_key_confidence_is_bounded():
    """Confidence is always clipped to [0, 1]."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, freq_hz=440.0, duration=2.0)
        tmp_path = f.name

    import librosa
    y, sr = librosa.load(tmp_path, sr=22050, mono=True)
    _, confidence = _detect_key(y, sr)

    assert confidence >= 0.0
    assert confidence <= 1.0


def test_detect_key_c_note_resolves_to_c_key():
    """A pure C tone (261.63 Hz) should yield a C key (major or minor).

    Chroma energy is concentrated on the C pitch class, so KS correlation
    peaks on one of the C profiles. This is a sanity check, not a strict
    accuracy requirement — a pure tone is ambiguous in mode.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, freq_hz=261.63, duration=4.0)
        tmp_path = f.name

    import librosa
    y, sr = librosa.load(tmp_path, sr=22050, mono=True)
    key, _ = _detect_key(y, sr)

    assert key.startswith("C"), f"expected a C key, got {key!r}"


# ── analyze_sample() ─────────────────────────────────────────────────────────

def test_analyze_sample_returns_match_object():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=3.0)
        path = f.name

    result = analyze_sample(path)

    assert isinstance(result, Match)


def test_analyze_sample_bpm_is_non_negative():
    # A pure sine wave has no rhythmic beat, so librosa may return 0.0 BPM.
    # We only assert it's a valid non-negative float, not that it found a beat.
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=3.0)
        path = f.name

    result = analyze_sample(path)
    assert result.bpm >= 0


def test_analyze_sample_key_is_string():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=3.0)
        path = f.name

    result = analyze_sample(path)
    assert isinstance(result.key, str)
    assert "major" in result.key or "minor" in result.key


def test_analyze_sample_source_is_local_analysis():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=3.0)
        path = f.name

    result = analyze_sample(path)
    assert result.source == "local_analysis"


def test_analyze_sample_confidence_in_range():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=3.0)
        path = f.name

    result = analyze_sample(path)
    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0


def test_analyze_sample_beat_pattern_bpm_in_reasonable_range():
    """A kick pattern at 120 BPM should be detected somewhere near 120 BPM
    (allowing for common half/double-time errors: ±50% is still a sane detection)."""
    target_bpm = 120.0
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_kick_pattern_wav(f.name, bpm=target_bpm, bars=8)
        path = f.name

    result = analyze_sample(path)
    # Allow for the common half/double-time error librosa can make
    ratio = result.bpm / target_bpm
    assert 0.4 < ratio < 2.6, f"BPM {result.bpm} too far from target {target_bpm}"


def test_analyze_sample_raises_runtime_error_when_librosa_missing():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _write_sine_wav(f.name, duration=1.0)
        path = f.name

    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "librosa":
            raise ImportError("No module named 'librosa'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(RuntimeError, match="librosa"):
            analyze_sample(path)
