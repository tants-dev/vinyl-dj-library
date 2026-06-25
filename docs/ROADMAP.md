# Roadmap

Phased build plan for the vinyl DJ library tool. Phases are ordered by dependency, not by date — no fixed deadlines, work through them in order. Check off items as they land and update [ARCHITECTURE_CURRENT.md](ARCHITECTURE_CURRENT.md) accordingly (see [CLAUDE.md](../CLAUDE.md)).

## Phase 0 — Foundations & API access

Goal: have everything needed to start pulling real data.

- [ ] Discogs personal access token obtained, collection folder ID identified.
- [x] GetSongBPM API key obtained and confirmed working live against the real API.
- [ ] Beatport API partner application submitted ([open risk, ADR-003](DECISIONS.md#adr-003-tiered-bpmkey-data-strategy--beatport-primary-getsongbpm-fallback-local-audio-analysis-last-resort-manual-override-always-available)) — track approval/denial here.
- [x] Python project scaffolded (`pyproject.toml`, dependencies, `.env` for secrets, gitignore for `vinyl_library.db` and `.env`).
- [x] SQLite schema created per [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md#4-data-model-sqlite) (`db/models.py`, created automatically on app startup).

## Phase 1 — Discogs collection sync

Goal: your real vinyl collection lives in the local database.

- [x] `sync/discogs_sync.py` pulls collection releases + full tracklists into SQLite.
- [x] Sync is idempotent and re-runnable (upsert, not duplicate) — Release matched by Discogs id, Track matched by (release_id, position) specifically so a re-sync never orphans a previously-enriched track's `BpmKeyData` by issuing it a new row id. Verified with a regression test.
- [x] Rate-limit handling for Discogs' 60 req/min cap — fixed 1.1s delay between requests (simpler and robust enough at this scale vs. parsing the `X-Discogs-Ratelimit-*` headers).
- [x] Manual trigger — the existing "Sync Discogs" button in the UI (`POST /sync`) now does the real thing instead of a stub.
- [x] Spot-check: synced the real collection — 42 releases, 348 tracks, all fields (artist credits incl. multi-artist joins, label, catalog #, year, format, cover art) verified correct against live API responses.

## Phase 2 — BPM/key enrichment pipeline

Goal: tracks get BPM/key automatically, with provenance tracked.

- [ ] Beatport source adapter (if/once partner access is approved).
- [x] GetSongBPM source adapter (`enrich/sources/getsongbpm.py`) — implemented and verified live against the real API with a real key (deadmau5 - Strobe, Daft Punk - One More Time, both matched correctly). Searches by title only and matches artist client-side (exact, normalized) — the API doesn't support server-side artist filtering despite what the docs imply.
- [x] Pipeline tries sources in priority order, stores `source` + `confidence` per [ADR-003](DECISIONS.md#adr-003-tiered-bpmkey-data-strategy--beatport-primary-getsongbpm-fallback-local-audio-analysis-last-resort-manual-override-always-available). Also now resilient to a single source erroring mid-batch (logs and moves on instead of aborting the rest of the tracks).
- [ ] Negative-result caching so dead-end lookups aren't repeated every run. **Explicitly deferred (2026-06-22)** — user wants to think about adding another data source for the 237 still-unresolved tracks before investing in caching the current source's misses.
- [x] Run against the real synced collection, eyeball match-rate and accuracy across the whole library. **111/348 tracks (~32%) matched** against the real 42-release collection. Spot-checked outliers (e.g. a 200 BPM result) against the raw API directly to rule out a matching bug — confirmed it's genuinely what GetSongBPM has on file (likely their own half/double-time tempo-detection ambiguity, a known characteristic of crowd-sourced BPM data), not a false match. See [ARCHITECTURE_CURRENT.md](ARCHITECTURE_CURRENT.md) for the real bug this run uncovered and fixed (artist fallback).

## Phase 3 — Local search & web UI

Goal: this is the thing you actually use while DJing.

- [x] FastAPI backend: `/search`, `/release/{id}` endpoints against local SQLite (instant, no network calls at search time).
- [x] Browser UI: search-as-you-type (htmx, vendored locally — no CDN dependency), results show cover art + BPM + key (Camelot and standard). Currently empty pending real data from Phase 1.
- [x] Release detail view with full tracklist.
- [ ] Confirm it's usable from a tablet/phone on the home network, not just the machine running the server.

## Phase 4 — Manual correction & local audio analysis fallback

Goal: cover the records that no database has — white labels, promos, dubplates, bootlegs.

- [x] `PATCH /track/{id}/bpm-key` manual override endpoint, plus an inline edit form on the release detail page (htmx, JSON-encoded submit, swaps in the updated BPM/key/source on save). Endpoint now accepts an optional `source` field (defaults `"manual"`) so clip analysis and tap results can be saved with the correct provenance.
- [ ] Manual values never get clobbered by re-running enrichment. Current protection is a side effect (pipeline skips any track with an existing `BpmKeyData` row, regardless of `source`), not an explicit guard — a future refactor that adds partial-update enrichment would need to check `source != "manual"` explicitly before overwriting.
- [x] Local audio analysis module (`librosa`) for needle-drop sample → BPM/key estimate (`enrich/audio_analysis.py`). BPM via `librosa.beat.beat_track(start_bpm=120)` (biased toward DJ tempos to reduce half/double-time ambiguity). Key via Krumhansl-Schmuckler chroma correlation over 24 pitch classes.
- [x] UI flow for recording/uploading a short sample for a specific track — full clip-analysis page built into `/analyze` (the renamed tap-BPM page), recording 20–30s of audio via Web Audio API `ScriptProcessorNode` → raw PCM → in-browser WAV encoder → `POST /analyze-clip`. Editable BPM result with ÷2/×2 buttons to correct half/double-time errors. Also available standalone (no track pre-selected) and from the release page via "Analyze this track" link.
- [x] Source/confidence clearly distinguishes manual and analyzed values from database matches in the UI — colour-coded source badges on every BPM/key cell (`getsongbpm` blue, `local_analysis` purple, `manual` amber, `beatport` orange). Overwrite confirmation (`hx-confirm` on manual edit form, `window.confirm()` in clip-analysis JS) when saving over existing data.
- [ ] Finer-grained source provenance on the Live BPM page: manual typing → `"manual"`, tap tempo → `"tapped"` (new source value), clip recording → `"local_analysis"` (already correct). Implementation: set `save-source` to `"tapped"` in `tap-bpm.js` when "Use this BPM →" is clicked (currently writes `"manual"`); listen for `input` on the shared BPM field to reset source back to `"manual"` when the user overrides a value by hand; add a `"tapped"` entry to `SOURCE_LABELS` in `bpm_key_cell.html` and extend the badge CSS.

## Phase 5 — Polish & DJ-specific workflow features

Goal: make it genuinely nice to use at the decks, not just functional.

- [x] Browsable list of all releases shown by default (before any search), filterable by year/genre/artist via dropdowns populated from the actual collection. Clicking a release opens the full release page; clicking a track from search results opens that track featured at the top (with its own manual-entry form immediately visible, no scrolling) with the full release underneath. None of the Discogs metadata shown (label, year, format, genres, styles) is clickable — confirmed live, the only link on the page is "back to search".
- [ ] Filter/sort by BPM range and by Camelot-compatible keys (harmonic mixing helper) — different from the year/genre/artist browse filters above, not yet built. **Explicitly deprioritized (2026-06-22)** per user — not a current focus.
- [x] "Last synced" status visible in UI — was hardcoded to `None` (always showed "Not synced yet" even after a real sync); now reads `max(Release.discogs_synced_at)` across the collection. Confirmed live against the real synced collection.
- [x] Sync/enrich triggerable from the UI — the "Sync Discogs" / "Enrich BPM/key" buttons have worked since the skeleton; both are now fully functional against real data.
- [ ] Large-type, glanceable layout tuned for tablet-at-the-decks use — works fine on a 768px tablet viewport today; not yet deliberately tuned for legibility-at-a-glance.
- [x] Live tap-tempo BPM counter (`GET /analyze`) — for records with no data at all, tap or press space in time with the beat, rolling average of last 8 taps, auto-resets after 2s gap. Now unified with clip analysis on the same page (see below). When arriving via `?track_id=X`, page shows track title + artist as "Now analyzing" header and both tools can save directly to that track.
- [x] Clip analysis and tap tempo unified on one page (`/analyze`, formerly `/tap-bpm`) with a shared track context: "Now analyzing: [Track] — [Artist]" header when a track is pre-selected; Record Clip and Tap Tempo panels side by side; shared "Save to track" section at the bottom with BPM + Key fields (auto-populated by whichever tool runs), a direct save button for the preset track, and a search field for any other track. "Use this BPM →" button on the tap panel feeds its result into the shared save section. Source set to `local_analysis` for clip results, `manual` for tap/typed values.

## Stretch / future ideas (not committed)

- System-tray launcher or PWA manifest so it feels more like an installed app.
- Barcode/cover-image based record recognition instead of typed search.
- "Crate" / session planning view (build a BPM-ordered setlist from owned records ahead of a set).
- Mic-based live BPM analysis of whatever's currently playing, on the `/tap-bpm` page above the tap counter (placeholder section already there) — analyze audio captured via the browser mic instead of manual tapping.
