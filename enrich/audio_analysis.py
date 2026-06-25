"""Local audio analysis for tracks no database covers
(white labels, promos, dubplates, bootlegs) — docs/ROADMAP.md Phase 4.

Requires the optional 'audio' extra: pip install -e '.[audio]'

BPM: librosa.beat.beat_track — reliable for electronic music (steady 4/4 grid).
Key: Krumhansl-Schmuckler key-finding over chroma features — ~70% accuracy for
     tonal music; less certain than a database match, so confidence is kept lower.
"""

from typing import Optional

from enrich.sources.base import Match

# Krumhansl-Schmuckler key profiles (tonic at index 0, chromatic ascending)
_KS_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_KS_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Enharmonic spellings that round-trip through enrich/camelot.py's _CAMELOT_MAP
_MAJOR_NOTES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_MINOR_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]


def _detect_key(y, sr) -> tuple:
    """Return (key_string, confidence) using chroma + KS correlation.

    np.roll(profile, i) shifts the profile so that pitch class i aligns with
    the tonic position (index 0), making the loop equivalent to testing each
    of the 24 possible keys in turn.
    """
    import librosa
    import numpy as np

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)  # 12-element vector, C at index 0

    best_corr = -2.0
    best_key = "C major"
    for i in range(12):
        for mode, profile, notes in [
            ("major", _KS_MAJOR, _MAJOR_NOTES),
            ("minor", _KS_MINOR, _MINOR_NOTES),
        ]:
            rotated = np.roll(profile, i)
            corr = float(np.corrcoef(chroma_mean, rotated)[0, 1])
            if corr > best_corr:
                best_corr = corr
                best_key = f"{notes[i]} {mode}"

    confidence = round(max(0.0, min(1.0, best_corr)), 3)
    return best_key, confidence


def analyze_sample(audio_file_path: str) -> Optional[Match]:
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError(
            "librosa is not installed. Install the 'audio' extra: "
            "pip install -e '.[audio]'"
        ) from exc

    import numpy as np

    y, sr = librosa.load(audio_file_path, sr=22050, mono=True)

    # start_bpm=120 biases the search toward common DJ tempos, reducing
    # the chance of locking onto a half-time or double-time pulse.
    tempo_raw, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120)
    bpm = round(float(np.atleast_1d(tempo_raw)[0]), 1)

    key, key_confidence = _detect_key(y, sr)

    return Match(
        bpm=bpm,
        key=key,
        source="local_analysis",
        confidence=round(key_confidence * 0.8, 3),
    )
