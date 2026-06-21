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
    static/
      htmx.min.js        -- vendored locally (not a CDN reference) so search stays offline
      style.css
```

**Verified working** (manually tested by booting `uvicorn api.main:app` and curling each route):
- `GET /` renders the search page, shows "0 tracks need BPM/key" against the empty DB.
- `GET /search?q=...` queries the local SQLite DB and returns an htmx partial — correctly returns "no matches" against the current empty DB.
- `POST /sync` returns a clear "DISCOGS_TOKEN is not set" message rather than crashing.
- `POST /enrich` runs the pipeline (a no-op against 0 tracks) and returns a status message.
- `GET /release/{id}` 404s correctly for a nonexistent release.
- Static assets (`htmx.min.js`, `style.css`) serve correctly.

**Not yet real:**
- No Discogs token/credentials provisioned — `sync_collection()` is structured but unimplemented past the rate-limit/pagination TODO.
- No GetSongBPM key, no Beatport partner access — both source adapters are stubs.
- The database is empty — there is no real vinyl collection data in it yet.
- No inline manual-edit UI (the `PATCH` endpoint works, but there's no button/form wired to it yet).
- Local audio analysis (`librosa`) is an optional extra, not installed by default, and unimplemented.

**Known environment gap:** [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md) specifies Python 3.12+, but the only Python available on this machine is system Python 3.9.6 (no `pyenv`/`uv`/Homebrew found). The project currently targets `>=3.9` in `pyproject.toml` so it actually runs here. This works fine for everything built so far, but should be revisited — see [DECISIONS.md](DECISIONS.md) ADR-006.

## Update log

- *(2026-06-21)* Repo created with planning docs only. No code.
- *(2026-06-21)* Pushed to GitHub as a private repo. Built and verified the runnable skeleton: SQLite schema, FastAPI app with search/release/sync/enrich/manual-override routes, htmx-based browser UI (vendored, offline), and stub sync/enrichment modules structured per the target architecture but not yet wired to real API credentials.
