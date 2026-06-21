# Current Architecture

What actually exists in this repo right now. Unlike [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md), this file describes reality, not intent — it should always match the state of the code. See [CLAUDE.md](../CLAUDE.md) for the rule that keeps it that way.

## Status: skeleton/shell built, no real data yet

The repo is on GitHub at [tants-dev/vinyl-dj-library](https://github.com/tants-dev/vinyl-dj-library) (private). The runnable shell of the app exists and has been verified to boot and serve requests, but it holds no real Discogs data and no BPM/key sources are wired up to real credentials yet.

```
vinyl-dj-library/
  CLAUDE.md
  pyproject.toml
  .env.example
  docs/
    ROADMAP.md
    ARCHITECTURE_CURRENT.md   (this file)
    ARCHITECTURE_TARGET.md
    DECISIONS.md
  db/
    models.py        -- Release, Track, BpmKeyData (SQLModel) — matches target schema
    session.py        -- SQLite engine + init_db(), auto-creates tables on app startup
  api/
    main.py            -- FastAPI app, mounts routers + static files, renders index page
    routes/
      search.py         -- GET /search (htmx partial, queries local SQLite)
      release.py        -- GET /release/{id}
      sync.py            -- POST /sync (wired to sync/discogs_sync.py, currently raises
                              a clear "not configured" message — no token yet)
      enrich.py          -- POST /enrich (wired to enrich/pipeline.py, currently a no-op
                              — no source APIs configured yet)
      track.py            -- PATCH /track/{id}/bpm-key (manual override, fully functional)
  sync/
    discogs_sync.py   -- structured per target arch, raises NotImplementedError —
                          Phase 1 work, blocked on a Discogs token
  enrich/
    pipeline.py        -- tries sources in priority order, functional once sources exist
    camelot.py           -- standard key -> Camelot wheel notation, fully implemented
    sources/
      beatport.py         -- stub, blocked on Beatport partner approval
      getsongbpm.py        -- stub, blocked on a GetSongBPM API key
    audio_analysis.py  -- stub, Phase 4, requires optional 'audio' extra (librosa)
  web/
    templates/          -- Jinja2: base, index (search page), release detail, results partial
      partials/
        bpm_key_cell.html -- shared BPM/key display + inline edit form, used in release.html
                              and as the htmx swap response from PATCH /track/{id}/bpm-key
    static/
      htmx.min.js        -- vendored locally (not a CDN reference) so search stays offline
      htmx-json-enc.js    -- vendored htmx extension, lets the edit form POST JSON bodies
                              matching the existing PATCH endpoint's contract
      style.css
```

**Tests:** `tests/` has 48 pytest cases covering everything with real logic — `enrich/camelot.py` (exhaustive Camelot wheel mapping), the `/search` query (matches across track/release/artist/label/catalog number, case-insensitivity, no-match and no-BPM-yet states), `/release/{id}` (happy path + 404), `/track/{id}/bpm-key` (create vs. update-in-place, always stamps `source="manual"`, unrecognized-key handling, plus the htmx-vs-JSON response branch), `/sync` and `/enrich` (correct messages when no credentials/sources are configured), and the index page's unenriched-track count. Uses an in-memory SQLite DB per test (`tests/conftest.py`, `StaticPool` + dependency override on `get_session`) — never touches the real `vinyl_library.db`. Run with `pytest` (after `pip install -e '.[dev]'`). The stub modules (`sync/discogs_sync.py`, `enrich/sources/beatport.py`, `enrich/sources/getsongbpm.py`, `enrich/audio_analysis.py`) have no tests yet — nothing to verify until they're implemented against real credentials.

**Verified working** (manually tested by booting `uvicorn api.main:app` and curling each route, plus a real browser pass via the preview tool with seeded data):
- `GET /` renders the search page, shows "0 tracks need BPM/key" against the empty DB.
- `GET /search?q=...` queries the local SQLite DB and returns an htmx partial — correctly returns "no matches" against the current empty DB; with real data, correctly returns matches with BPM/Camelot key.
- `POST /sync` returns a clear "DISCOGS_TOKEN is not set" message rather than crashing.
- `POST /enrich` runs the pipeline (a no-op against 0 tracks) and returns a status message.
- `GET /release/{id}` 404s correctly for a nonexistent release; with real data, renders the tracklist with an inline BPM/key edit form per track.
- Inline manual edit: filling the BPM/key form and submitting sends a JSON-encoded `PATCH /track/{id}/bpm-key`, persists to SQLite, computes the Camelot key (e.g. "A minor" → "8A"), and swaps the updated value into the page — confirmed visible afterward on both the release page and `/search`.
- Static assets (`htmx.min.js`, `htmx-json-enc.js`, `style.css`) serve correctly.

**Not yet real:**
- No Discogs token/credentials provisioned — `sync_collection()` is structured but unimplemented past the rate-limit/pagination TODO.
- No GetSongBPM key, no Beatport partner access — both source adapters are stubs.
- The database is empty — there is no real vinyl collection data in it yet.
- Local audio analysis (`librosa`) is an optional extra, not installed by default, and unimplemented.
- It's not yet guaranteed that re-running enrichment can't clobber a manual value for a *different* source's match — the pipeline currently only enriches tracks with no `BpmKeyData` row at all (any existing row, manual or otherwise, blocks re-enrichment), which satisfies the "never clobber manual" requirement as a side effect but hasn't been tested against a real overwrite scenario since no automated source is live yet.

**Known environment gap:** [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md) specifies Python 3.12+, but the only Python available on this machine is system Python 3.9.6 (no `pyenv`/`uv`/Homebrew found). The project currently targets `>=3.9` in `pyproject.toml` so it actually runs here. This works fine for everything built so far, but should be revisited — see [DECISIONS.md](DECISIONS.md) ADR-006.

## Update log

- *(2026-06-21)* Repo created with planning docs only. No code.
- *(2026-06-21)* Pushed to GitHub as a private repo. Built and verified the runnable skeleton: SQLite schema, FastAPI app with search/release/sync/enrich/manual-override routes, htmx-based browser UI (vendored, offline), and stub sync/enrichment modules structured per the target architecture but not yet wired to real API credentials.
- *(2026-06-21)* Added a pytest suite (47 tests) covering all routes and the Camelot mapping. Replaced deprecated `@app.on_event("startup")` with a `lifespan` context manager and updated `TemplateResponse` calls to the new (request, name, context) argument order — both surfaced as deprecation warnings once tests existed to catch them.
- *(2026-06-21)* Built the inline manual BPM/key edit form on the release detail page (`web/templates/partials/bpm_key_cell.html`), shared between the initial render and the `PATCH /track/{id}/bpm-key` htmx response. Vendored the `htmx-json-enc` extension so the form posts JSON without changing the existing API contract. Verified end-to-end in a real browser with seeded data: edit → save → Camelot key computed → reflected on both the release page and search results. Added a test for the new htmx response branch (48 tests total).
