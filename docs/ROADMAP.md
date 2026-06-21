# Roadmap

Phased build plan for the vinyl DJ library tool. Phases are ordered by dependency, not by date — no fixed deadlines, work through them in order. Check off items as they land and update [ARCHITECTURE_CURRENT.md](ARCHITECTURE_CURRENT.md) accordingly (see [CLAUDE.md](../CLAUDE.md)).

## Phase 0 — Foundations & API access

Goal: have everything needed to start pulling real data.

- [ ] Discogs personal access token obtained, collection folder ID identified.
- [ ] GetSongBPM API key obtained.
- [ ] Beatport API partner application submitted ([open risk, ADR-003](DECISIONS.md#adr-003-tiered-bpmkey-data-strategy--beatport-primary-getsongbpm-fallback-local-audio-analysis-last-resort-manual-override-always-available)) — track approval/denial here.
- [x] Python project scaffolded (`pyproject.toml`, dependencies, `.env` for secrets, gitignore for `vinyl_library.db` and `.env`).
- [x] SQLite schema created per [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md#4-data-model-sqlite) (`db/models.py`, created automatically on app startup).

## Phase 1 — Discogs collection sync

Goal: your real vinyl collection lives in the local database.

- [ ] `sync/discogs_sync.py` pulls collection releases + full tracklists into SQLite.
- [ ] Sync is idempotent and re-runnable (upsert, not duplicate).
- [ ] Rate-limit handling for Discogs' 60 req/min cap.
- [ ] Manual trigger (CLI command or script) to run a sync.
- [ ] Spot-check: sync your real collection once, confirm release/track counts look right.

## Phase 2 — BPM/key enrichment pipeline

Goal: tracks get BPM/key automatically, with provenance tracked.

- [ ] Beatport source adapter (if/once partner access is approved).
- [x] GetSongBPM source adapter (`enrich/sources/getsongbpm.py`) — implemented and unit-tested against a mocked API; not yet exercised against a real key, since none is provisioned (Phase 0 still open on that).
- [x] Pipeline tries sources in priority order, stores `source` + `confidence` per [ADR-003](DECISIONS.md#adr-003-tiered-bpmkey-data-strategy--beatport-primary-getsongbpm-fallback-local-audio-analysis-last-resort-manual-override-always-available). Also now resilient to a single source erroring mid-batch (logs and moves on instead of aborting the rest of the tracks).
- [ ] Negative-result caching so dead-end lookups aren't repeated every run.
- [ ] Run against the real synced collection, eyeball match-rate and accuracy on a sample of known tracks. Blocked on getting a real `GETSONGBPM_API_KEY` and on Phase 1 (Discogs sync) landing first.

## Phase 3 — Local search & web UI

Goal: this is the thing you actually use while DJing.

- [x] FastAPI backend: `/search`, `/release/{id}` endpoints against local SQLite (instant, no network calls at search time).
- [x] Browser UI: search-as-you-type (htmx, vendored locally — no CDN dependency), results show cover art + BPM + key (Camelot and standard). Currently empty pending real data from Phase 1.
- [x] Release detail view with full tracklist.
- [ ] Confirm it's usable from a tablet/phone on the home network, not just the machine running the server.

## Phase 4 — Manual correction & local audio analysis fallback

Goal: cover the records that no database has — white labels, promos, dubplates, bootlegs.

- [x] `PATCH /track/{id}/bpm-key` manual override endpoint, plus an inline edit form on the release detail page (htmx, JSON-encoded submit, swaps in the updated BPM/key/source on save).
- [ ] Manual values never get clobbered by re-running enrichment.
- [ ] Local audio analysis module (`librosa`/`essentia`) for needle-drop sample → BPM/key estimate.
- [ ] UI flow for recording/uploading a short sample for a specific track.
- [ ] Source/confidence clearly distinguishes manual and analyzed values from database matches in the UI.

## Phase 5 — Polish & DJ-specific workflow features

Goal: make it genuinely nice to use at the decks, not just functional.

- [ ] Filter/sort by BPM range and by Camelot-compatible keys (harmonic mixing helper).
- [ ] "Last synced" / "N tracks need enrichment" status visible in UI.
- [ ] Sync/enrich triggerable from the UI, not just CLI.
- [ ] Large-type, glanceable layout tuned for tablet-at-the-decks use.

## Stretch / future ideas (not committed)

- System-tray launcher or PWA manifest so it feels more like an installed app.
- Barcode/cover-image based record recognition instead of typed search.
- "Crate" / session planning view (build a BPM-ordered setlist from owned records ahead of a set).
