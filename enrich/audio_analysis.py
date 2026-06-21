"""Local audio analysis fallback for tracks no database covers
(white labels, promos, dubplates, bootlegs) — docs/ROADMAP.md Phase 4.

Requires the optional 'audio' extra (librosa). Not yet implemented.
"""

from typing import Optional

from enrich.sources.base import Match


def analyze_sample(audio_file_path: str) -> Optional[Match]:
    try:
        import librosa  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "librosa is not installed. Install the 'audio' extra: "
            "pip install -e '.[audio]'"
        ) from exc

    # TODO (Phase 4): load audio_file_path, run tempo estimation and a
    # chroma-based key estimate, return Match(source="local_analysis",
    # confidence=...). Confidence should be lower than database matches.
    raise NotImplementedError("Local audio analysis not yet implemented")
