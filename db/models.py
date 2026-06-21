from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Release(SQLModel, table=True):
    """A Discogs release in the user's collection (one piece of vinyl)."""

    id: int = Field(primary_key=True, description="Discogs release id")
    title: str
    artists: str
    label: Optional[str] = None
    catalog_number: Optional[str] = None
    year: Optional[int] = None
    format: Optional[str] = None
    genres: Optional[str] = None
    styles: Optional[str] = None
    cover_image_url: Optional[str] = None
    discogs_synced_at: Optional[str] = None

    tracks: List["Track"] = Relationship(back_populates="release")


class Track(SQLModel, table=True):
    """A single track on a release, e.g. position 'A1'."""

    id: Optional[int] = Field(default=None, primary_key=True)
    release_id: int = Field(foreign_key="release.id")
    position: str
    title: str
    artists: Optional[str] = None
    duration: Optional[str] = None

    release: Optional[Release] = Relationship(back_populates="tracks")
    bpm_key: Optional["BpmKeyData"] = Relationship(back_populates="track")


class BpmKeyData(SQLModel, table=True):
    """BPM/key for a track, with provenance. One row per track."""

    track_id: Optional[int] = Field(
        default=None, foreign_key="track.id", primary_key=True
    )
    bpm: Optional[float] = None
    key: Optional[str] = None
    camelot_key: Optional[str] = None
    source: Optional[str] = Field(
        default=None,
        description="'beatport' | 'getsongbpm' | 'local_analysis' | 'manual'",
    )
    confidence: Optional[float] = None
    matched_at: Optional[str] = None

    track: Optional[Track] = Relationship(back_populates="bpm_key")
