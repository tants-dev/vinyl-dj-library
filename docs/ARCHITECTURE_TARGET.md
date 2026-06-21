# Target Architecture

What this system should look like once the roadmap is complete. See [DECISIONS.md](DECISIONS.md) for the reasoning behind these choices, and [ARCHITECTURE_CURRENT.md](ARCHITECTURE_CURRENT.md) for what actually exists today.

## Goal

Type or scan a record you own → instantly see every track's BPM and key, sourced from your real Discogs collection, while standing at the decks with no internet dependency at lookup time.

## High-level data flow

```
 ┌─────────────┐      sync (manual,         ┌────────────────┐
 │  Discogs API │ ───  occasional)  ───────▶ │   SQLite DB     │
 └─────────────┘                             │ (source of      │
                                              │  truth, local)  │
 ┌─────────────┐                             │                 │
 │ Beatport API │ ─┐                         │  releases       │
 └─────────────┘  │   enrichment pipeline    │  tracks         │
 ┌─────────────┐  ├─ (per unenriched track, ▶│  bpm_key_data   │
 │GetSongBPM API│ ─┤   tries sources in       │  (provenance    │
 └─────────────┘  │   priority order)         │   per value)    │
 ┌─────────────┐  │                          └────────┬────────┘
 │Local audio   │ ─┘                                   │
 │analysis      │                                      │ read-only,
 └─────────────┘                                       │ instant
                                                         ▼
                                              ┌────────────────┐
                                              │ FastAPI backend │
                                              │  /search        │
                                              │  /release/{id}  │
                                              │  /sync          │
                                              │  /enrich        │
                                              └────────┬────────┘
                                                        │
                                                        ▼
                                              ┌────────────────┐
                                              │  Browser UI     │
                                              │  (search-first, │
                                              │  big BPM/key    │
                                              │  display)       │
                                              └────────────────┘
```

Two distinct workflows, deliberately decoupled:
- **Sync/enrich** — slow, network-dependent, run occasionally (when records are bought). Writes to SQLite.
- **Search** — instant, fully local, read-only against SQLite. This is the only thing that happens live while DJing.

## Components

### 1. Discogs sync module (`sync/discogs_sync.py`)
- Authenticates with a Discogs personal access token (simplest option for accessing only your own collection — no need for full OAuth flow).
- Pulls the user's collection folder(s) via `GET /users/{username}/collection/folders/{folder_id}/releases`.
- For each release, fetches full release detail (tracklist, artists, label, catalog number, year, genre/style, cover art URL).
- Upserts into the `releases` and `tracks` tables, keyed by Discogs release ID.
- Respects Discogs rate limit (60 req/min authenticated) with simple throttling/backoff.
- Idempotent — safe to re-run; only changed records are touched.

### 2. Enrichment pipeline (`enrich/pipeline.py`)
- Runs over tracks that have no BPM/key yet, or whose data is stale.
- For each track, tries sources in priority order per [ADR-003](DECISIONS.md#adr-003-tiered-bpmkey-data-strategy--beatport-primary-getsongbpm-fallback-local-audio-analysis-last-resort-manual-override-always-available):
  1. Beatport API match by artist + title (+ catalog number/label if it helps disambiguate).
  2. GetSongBPM API match by artist + title.
  3. (Optional, user-triggered) local audio analysis from a recorded needle-drop sample.
- Stores match confidence and `source` provenance alongside the BPM/key value.
- Never overwrites a `manual` source value on re-run.
- Caches negative results (no match found) with a timestamp so the pipeline doesn't re-hit the same dead end on every run — but allows manual re-trigger per track.

### 3. Local audio analysis module (`enrich/audio_analysis.py`)
- For tracks with no database match (common for white labels, promos, dubplates, bootlegs).
- User records a short sample (mic or phono/line-in capture) through the UI or a simple CLI helper.
- Uses `librosa` (tempo estimation) and a key-detection approach (e.g. chroma-based Krumhansl-Schmuckler, or `essentia`'s key extractor) to estimate BPM/key directly from audio.
- Lower confidence than database matches by nature — flagged distinctly in the UI so the user knows it's an estimate, not a verified label/database value.

### 4. Data model (SQLite)

```
releases
  id (Discogs release id, PK)
  title, artists, label, catalog_number, year, format, genres, styles
  cover_image_url
  discogs_synced_at

tracks
  id (PK)
  release_id (FK -> releases.id)
  position        -- e.g. "A1", "B2"
  title
  artists          -- may differ from release artist (remixes, comps)
  duration

bpm_key_data
  track_id (FK -> tracks.id)
  bpm
  key              -- standard notation, e.g. "A minor"
  camelot_key      -- derived, e.g. "8A" — for harmonic mixing at a glance
  source           -- 'beatport' | 'getsongbpm' | 'local_analysis' | 'manual'
  confidence       -- nullable, source-dependent
  matched_at
```

`camelot_key` is derived/stored alongside standard key notation since Camelot wheel notation is what DJs actually use for harmonic mixing — computing it at write time avoids a lookup-table join on every search.

### 5. FastAPI backend (`api/main.py`)
- `GET /search?q=...` — fuzzy search across artist/title/label/catalog number, returns release+track+BPM/key, instant (local SQLite query only).
- `GET /release/{id}` — full release detail with all tracks and their BPM/key.
- `POST /sync` — triggers a Discogs collection sync.
- `POST /enrich` — triggers the enrichment pipeline over unenriched tracks.
- `PATCH /track/{id}/bpm-key` — manual override entry point.
- No auth — bound to localhost by default; LAN access is the user's own network, not exposed publicly.

### 6. Browser UI (`web/`)
- Server-rendered (Jinja2) with light htmx/JS for instant search-as-you-type, no SPA build step (per [ADR-002](DECISIONS.md#adr-002-python--fastapi--sqlite-as-the-core-stack)).
- Search-first landing page: type artist/title/label/catalog number → results show cover art, BPM, key (Camelot + standard), source badge.
- Release detail view: full tracklist with per-track BPM/key, inline manual-edit.
- Sync/enrich status indicator ("last synced: ...", "12 tracks need enrichment").
- Designed to be legible at a glance on a tablet propped up near turntables — large type for BPM/key, minimal clicking.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI + Uvicorn |
| Database | SQLite (single file, `vinyl_library.db`) |
| DB access | SQLModel or plain `sqlite3` — TBD at implementation time |
| Frontend | Jinja2 templates + htmx, no JS build step |
| Discogs client | `python3-discogs-client` or direct `httpx` calls against Discogs REST API |
| BPM/key APIs | Beatport API (partner-gated, pending access), GetSongBPM REST API |
| Audio analysis (optional) | `librosa`, possibly `essentia` |
| Packaging | `uv` or `pip` + `requirements.txt`/`pyproject.toml`; run via `uvicorn` locally |

## Proposed folder structure

```
vinyl-dj-library/
  CLAUDE.md
  docs/
    ROADMAP.md
    ARCHITECTURE_CURRENT.md
    ARCHITECTURE_TARGET.md
    DECISIONS.md
  api/
    main.py
    routes/
  sync/
    discogs_sync.py
  enrich/
    pipeline.py
    sources/
      beatport.py
      getsongbpm.py
    audio_analysis.py
  db/
    models.py
    migrations/
  web/
    templates/
    static/
  vinyl_library.db      -- gitignored, local data
  .env                  -- gitignored, API keys/tokens
  pyproject.toml
```

## Out of scope (for now)

- Multi-user support, cloud sync, mobile app.
- Automatic record recognition (e.g. camera/barcode scanning a sleeve) — manual search is the v1 interaction model.
- Streaming-service track matching (Spotify audio-features is largely unavailable to new API apps as of late 2024, and isn't needed for a vinyl-only collection anyway).
