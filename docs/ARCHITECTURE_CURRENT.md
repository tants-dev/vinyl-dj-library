# Current Architecture

What actually exists in this repo right now. Unlike [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md), this file describes reality, not intent — it should always match the state of the code. See [CLAUDE.md](../CLAUDE.md) for the rule that keeps it that way.

## Status: real data flowing end-to-end — Discogs sync + GetSongBPM enrichment both live

The repo is on GitHub at [tants-dev/vinyl-dj-library](https://github.com/tants-dev/vinyl-dj-library) (**public** — required for the GetSongBPM API key's mandatory backlink, see README.md Credits). The app boots, serves requests, and now holds the user's real Discogs collection: **42 releases, 348 tracks**, synced from the real account, with **111 tracks (~32%) auto-enriched** with real BPM/key data from GetSongBPM. Both `DISCOGS_TOKEN`/`DISCOGS_USERNAME` and `GETSONGBPM_API_KEY` are configured locally in `.env` (gitignored, never committed).

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
      search.py         -- GET /search (htmx partial, queries local SQLite). Branches on
                              whether q is empty: empty -> browse_releases() (the default
                              release list, filterable by year/genre/artist via query
                              params); non-empty -> track-level search as before, now
                              linking each result to /track/{id} instead of /release/{id}.
                              year is accepted as a raw string and parsed manually, not
                              as Optional[int] -- FastAPI 422s on year="" (an unselected
                              <select> submits empty string, not an absent param), a real
                              bug only caught by testing the actual route, not by calling
                              browse_releases() directly in tests.
      release.py        -- GET /release/{id} (full release page, no featured track)
      track.py            -- GET /track/{id} (same release.html template, with that one
                              track passed as featured_track so it renders prominently at
                              the top with its own manual-entry form, full release/
                              tracklist underneath); PATCH /track/{id}/bpm-key (manual
                              override, fully functional)
      sync.py            -- POST /sync (wired to sync/discogs_sync.py, fully functional;
                              catches httpx.HTTPError so a Discogs failure shows a
                              message instead of a 500)
      enrich.py          -- POST /enrich (wired to enrich/pipeline.py, fully functional;
                              message text reflects whether any source is actually
                              configured, not a hardcoded "not configured" string)
      system.py            -- POST /shutdown (self-SIGTERM, for the UI Quit button)
  sync/
    discogs_sync.py   -- fully implemented and verified against the real account
                          (42 releases, 348 tracks). Two-step fetch: paginate the
                          collection-folder listing for release ids, then GET full
                          release detail per id (only the detail endpoint has the
                          tracklist). Release upserted by Discogs id; Track upserted
                          by (release_id, position), specifically NOT delete-and-
                          reinsert, so re-syncing never orphans a previously
                          enriched track's BpmKeyData by giving it a new row id
                          (regression-tested). Fixed 1.1s delay between requests
                          for the 60 req/min rate limit. Artist credits reconstructed
                          from Discogs' per-artist "join" field to match what
                          their own artists_sort field produces — verified against
                          4 real multi-artist releases, including an early wrong
                          guess (comma needs no leading space, unlike every other
                          join type) caught by checking real data instead of
                          assuming.
  enrich/
    pipeline.py        -- tries sources in priority order; a source raising an
                          HTTP error mid-batch is logged and skipped rather
                          than aborting the rest of the tracks. Falls back to the
                          track's release.artists when Track.artists is None
                          (true for any non-compilation vinyl) — this was a real
                          bug found by running enrichment against the actual
                          collection: every lookup was silently searching with an
                          empty artist string and getting 0/348 matches before the
                          fix, 111/348 after.
    camelot.py           -- standard key -> Camelot wheel notation, fully implemented
    sources/
      beatport.py         -- stub, blocked on Beatport partner approval
      getsongbpm.py        -- fully implemented and verified live with a real
                              API key against real tracks (deadmau5 - Strobe,
                              Daft Punk - One More Time). Searches by title
                              only (the API doesn't filter by artist
                              server-side — confirmed empirically), then picks
                              the matching artist out of the results by exact
                              normalized name match (not substring, to avoid
                              false positives like "Air" matching "Fairground
                              Attraction"). Normalizes the API's unicode sharp
                              sign ("♯", not ASCII "#") and enharmonic
                              spelling (e.g. "C#"/"Db") to match camelot.py's
                              table. Reuses a single pooled httpx.Client
                              across all lookups (lazily created, module-level)
                              instead of a fresh connection per call — measured
                              2.5x faster (~173ms -> ~68-77ms per request)
                              against the real API.
    audio_analysis.py  -- stub, Phase 4, requires optional 'audio' extra (librosa)
  web/
    templates/          -- Jinja2: base, index (browsable release list + filters + search),
                              release detail (also doubles as the track-detail page when a
                              featured_track is passed)
      partials/
        bpm_key_cell.html -- shared BPM/key display + inline edit form. Takes an optional
                              editable flag (defaults true) so the same track's BPM/key can
                              be rendered twice on the track-detail page (once prominently
                              featured, once in its normal tracklist position) without a
                              duplicate DOM id or two htmx-editable forms targeting the same
                              element — only the featured instance is editable/has an id.
        release_list.html  -- the browsable release list (used both for the index page's
                              default view and the filtered /search?q= response)
    static/
      htmx.min.js        -- vendored locally (not a CDN reference) so search stays offline
      htmx-json-enc.js    -- vendored htmx extension, lets the edit form POST JSON bodies
                              matching the existing PATCH endpoint's contract
      style.css
```

A "Quit" button is fixed in the top-right corner on every page (added to `base.html`), confirms before firing, and POSTs to `/shutdown`.

**Tests:** `tests/` has 156 pytest cases covering everything with real logic — `enrich/camelot.py` (exhaustive Camelot wheel mapping), `enrich/sources/getsongbpm.py` (request shape — title-only search, since the API doesn't filter by artist server-side; artist-matching is exact-normalized, not substring, with a regression test for the "Air"/"Fairground Attraction" false-positive case; the dict-shaped "no result" response; unicode sharp-sign handling; HTTP error propagation; every enharmonic key spelling round-tripping through `to_camelot()`), `sync/discogs_sync.py` (pagination, the Release/Track upsert behavior, the Track-id-preservation-on-resync regression test, the artist-join formatting verified against real multi-artist examples, missing-credential and HTTP-error errors), `enrich/pipeline.py` (a source raising mid-batch doesn't abort the rest of the tracks; the release-artist-fallback regression test; track-level artist takes priority over release-level when both present), `api/routes/search.py`'s `browse_releases`/`get_filter_options` (year/genre/artist filtering and combinations, distinct-value dedup) plus a regression test hitting the real `/search` route (not just the helper function) with the empty-string filter params an unselected `<select>` actually sends — this is the test that would have caught the `year: Optional[int]` 422 bug if it had existed before the live-browser pass found it, `/track/{id}` GET (featured track + full release render, manual-entry form positioned before the tracklist, no duplicate `bpm-key-{id}` DOM id, only one `<a>` tag — "back to search" — on the whole page, 404), the `/search` query (matches across track/release/artist/label/catalog number, case-insensitivity, no-match and no-BPM-yet states), `/release/{id}` (happy path + 404, no featured-track block), `/track/{id}/bpm-key` PATCH (create vs. update-in-place, always stamps `source="manual"`, unrecognized-key handling, plus the htmx-vs-JSON response branch), `/sync` and `/enrich` (correct messages depending on whether any source is configured), `/shutdown` (mocks `os.kill` so the suite doesn't kill itself), and the index page's unenriched-track count. Uses an in-memory SQLite DB per test (`tests/conftest.py`, `StaticPool` + dependency override on `get_session`) — never touches the real `vinyl_library.db`. Run with `pytest` (after `pip install -e '.[dev]'`). The stub modules (`enrich/sources/beatport.py`, `enrich/audio_analysis.py`) have no tests yet — nothing to verify until they're implemented against real credentials.

**Verified working** (manually tested by booting `uvicorn api.main:app` and curling each route, several real browser passes via the preview tool, and full runs against the real Discogs account):
- `GET /` renders the browsable release list by default (all 42 real releases, cover art, label/catalog/year), with year/genre/artist filter dropdowns populated from the real collection's actual distinct values — confirmed live that selecting "Electronic" correctly narrows the list.
- `GET /search?q=...` queries the local SQLite DB and returns an htmx partial with real BPM/Camelot key data; each result links to `/track/{id}`.
- `GET /track/{id}` — confirmed live: clicking a search result (e.g. Aaliyah - "Beats 4 Da Streets (Intro)") opens that track featured at the top with its manual-entry form immediately visible (no scrolling), the full release's Discogs metadata (label, year, format, genres, styles) underneath as plain text, and the complete tracklist below that — with the featured track's *own* row in that tracklist correctly showing no second edit form (avoiding the duplicate-DOM-id problem). Confirmed via `document.querySelectorAll('a')` that the only link on the page is "back to search" — nothing else is clickable.
- `POST /sync` — ran for real: 42 releases, 348 tracks synced from the live Discogs account in ~68s. Artist credits, label, catalog number, year, format, genres, styles, and cover art all spot-checked correct. Re-running it is idempotent and was confirmed not to duplicate or re-id existing rows.
- `POST /enrich` — ran for real against the synced collection: 111/348 tracks (~32%) matched via GetSongBPM. A few outlier results (e.g. a 200 BPM match) were checked directly against the raw API to rule out a matching bug before being accepted as genuine data-source noise (see "Known data-quality caveat" below).
- `GET /release/{id}` 404s correctly for a nonexistent release; with real data, renders the tracklist with an inline BPM/key edit form per track, pre-filled with enriched values.
- Inline manual edit: filling the BPM/key form and submitting sends a JSON-encoded `PATCH /track/{id}/bpm-key`, persists to SQLite, computes the Camelot key (e.g. "A minor" → "8A"), and swaps the updated value into the page — confirmed visible afterward on both the release page and `/search`.
- Quit button: clicking it (after confirming the dialog) sends `POST /shutdown`, and the server process fully exits — confirmed at the OS level (`pgrep` no longer found it after clicking, not just that the HTTP connection dropped).
- Static assets (`htmx.min.js`, `htmx-json-enc.js`, `style.css`) serve correctly.

**Known data-quality caveat:** GetSongBPM is a free, crowd-sourced database. Spot-checking an outlier (Aaliyah - "4 Page Letter" matched at 200 BPM) against the raw API confirmed it's genuinely what's on file for that exact artist/title — not a false match — most likely a half/double-time tempo-detection ambiguity on GetSongBPM's end, which is common for syncopated genres (R&B, hip-hop). This is a property of the data source, not a bug in this codebase; not something to silently "correct" with guesswork.

**Not yet real:**
- No Beatport partner access — that source adapter is still a stub.
- Local audio analysis (`librosa`) is an optional extra, not installed by default, and unimplemented.
- It's not yet guaranteed that re-running enrichment can't clobber a manual value for a *different* source's match — the pipeline currently only enriches tracks with no `BpmKeyData` row at all (any existing row, manual or otherwise, blocks re-enrichment), which satisfies the "never clobber manual" requirement as a side effect but hasn't been tested against a real overwrite scenario.
- Negative-result caching isn't implemented — re-running `/enrich` re-attempts the 237 unmatched tracks from scratch every time rather than remembering they failed last run.

**Known environment gap:** [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md) specifies Python 3.12+, but the only Python available on this machine is system Python 3.9.6 (no `pyenv`/`uv`/Homebrew found). The project currently targets `>=3.9` in `pyproject.toml` so it actually runs here. This works fine for everything built so far, but should be revisited — see [DECISIONS.md](DECISIONS.md) ADR-006.

**Dev tooling note:** the agent's own preview-tool launch config (`/Users/tants/src/.claude/launch.json`, outside this repo) runs the dev server on port 8001, not 8000, specifically so it doesn't collide with a manually-started `uvicorn api.main:app --reload` (which the user runs on the default port 8000 per the README). Both point at the same `vinyl_library.db`.

## Update log

- *(2026-06-21)* Repo created with planning docs only. No code.
- *(2026-06-21)* Pushed to GitHub as a private repo. Built and verified the runnable skeleton: SQLite schema, FastAPI app with search/release/sync/enrich/manual-override routes, htmx-based browser UI (vendored, offline), and stub sync/enrichment modules structured per the target architecture but not yet wired to real API credentials.
- *(2026-06-21)* Added a pytest suite (47 tests) covering all routes and the Camelot mapping. Replaced deprecated `@app.on_event("startup")` with a `lifespan` context manager and updated `TemplateResponse` calls to the new (request, name, context) argument order — both surfaced as deprecation warnings once tests existed to catch them.
- *(2026-06-21)* Built the inline manual BPM/key edit form on the release detail page (`web/templates/partials/bpm_key_cell.html`), shared between the initial render and the `PATCH /track/{id}/bpm-key` htmx response. Vendored the `htmx-json-enc` extension so the form posts JSON without changing the existing API contract. Verified end-to-end in a real browser with seeded data: edit → save → Camelot key computed → reflected on both the release page and search results. Added a test for the new htmx response branch (48 tests total).
- *(2026-06-21)* Added `POST /shutdown` and a Quit button (fixed top-right, every page) so the server can be stopped from the UI instead of the terminal. Sends `SIGTERM` to its own process. Test mocks `os.kill` to verify the signal without killing the test run. Verified live: clicking it actually terminated the OS process, not just the HTTP connection (49 tests total).
- *(2026-06-21)* Implemented `enrich/sources/getsongbpm.py` for real: hits `GET https://api.getsong.co/search/`, parses `tempo` and `key_of`, and normalizes GetSongBPM's enharmonic key spelling (e.g. "C#"/"Db") to match `enrich/camelot.py`'s table so every parsed key round-trips to a real Camelot code — verified with a parametrized test covering all 24 keys. Confirmed live against the real (unauthenticated) endpoint that the URL/params/error shape match what the code expects, without a real API key (none provisioned yet). Also hardened `enrich/pipeline.py` so one source raising an HTTP error mid-batch is logged and skipped instead of aborting every other track. 57 new tests added (106 total).
- *(2026-06-21)* Got a real `GETSONGBPM_API_KEY` and tested against the live API — found and fixed two real bugs the unauthenticated/mocked testing couldn't catch: (1) the API ignores artist filtering entirely (the assumed `song:{title} artist:{artist}` combined lookup syntax just searches that literal string and matches nothing) — rewrote to search by title only and pick the matching artist out of the results client-side, by exact normalized name rather than substring (substring matching produced a real false positive: "Air" matching "Fairground Attraction"); (2) `key_of` uses the unicode sharp sign "♯" (U+266F), not ASCII "#", which silently broke every sharp-key parse — now normalized before lookup. Verified end-to-end through the real running app: seeded deadmau5 - Strobe and Daft Punk - One More Time, hit the Enrich button, got back 128 BPM/G# minor and 122 BPM/D major respectively — both match known real-world values. Also fixed a stale hardcoded "no sources configured" message on `/enrich` that no longer reflected reality once a source was actually live. Repo made public (was private) to satisfy GetSongBPM's mandatory backlink requirement; added a Credits section to README.md. 13 net new/changed tests (119 total).
- *(2026-06-21)* Implemented `sync/discogs_sync.py` for real and got a real Discogs token. Verified the full collection/release-detail contract against the live API before writing code (pagination shape, that tracklist only exists on the per-release detail endpoint, the artist "join" field convention, rate-limit headers). Caught and fixed a real formatting bug by checking against actual multi-artist releases: commas don't get a leading space in Discogs' own `artists_sort`, unlike every other join type ("Prozak (11), Silva Bumpa" not "Prozak (11) , Silva Bumpa") — the fix was verified against 4 real multi-artist releases. Designed the Track upsert to match by `(release_id, position)` rather than delete-and-reinsert specifically so re-syncing can never orphan a previously-enriched track's `BpmKeyData` by giving it a new row id — regression-tested. Ran the real sync: 42 releases, 348 tracks, all spot-checked correct (e.g. Underworld - Born Slippy).
- *(2026-06-21)* Ran `enrich_unmatched_tracks()` against the real synced collection for the first time and got 0/348 matches — investigated rather than accepting that as "low coverage," and found a real bug in `enrich/pipeline.py`: it was passing `track.artists or ""` to the lookup, but `Track.artists` is `None` for any non-compilation release (the real artist credit lives on `Release.artists`, exactly the fallback `api/routes/search.py` already used for display) — so every single lookup was silently searching with an empty artist string. Fixed the pipeline to use the same release-artist fallback, with a regression test capturing the exact artist string passed to the source. Re-ran enrichment: 111/348 tracks (~32%) matched for real. Spot-checked an outlier (a 200 BPM result) directly against the raw API before accepting it, to rule out a matching bug rather than assume — confirmed it's genuine data-source noise, not a false match. 16 net new/changed tests (135 total).
- *(2026-06-21)* Post-MVP UI pass: (1) the index page now shows a browsable list of all releases by default instead of "Start typing", filterable by year/genre/artist via dropdowns populated from the actual collection (`browse_releases`/`get_filter_options` in `api/routes/search.py`); (2) added `GET /track/{id}`, which reuses `release.html` with that track passed as `featured_track` so it renders prominently at the top — with its own manual-entry form immediately visible, no scrolling — followed by the full release's Discogs metadata and complete tracklist; search results now link to `/track/{id}` instead of `/release/{id}`. `bpm_key_cell.html` gained an `editable` flag to avoid a duplicate DOM id when the featured track also appears in the tracklist below it. Confirmed live that none of the Discogs metadata is clickable (only link on the page is "back to search"). A live browser pass (not just the test suite) caught a real bug the tests missed: the `/search` route declared `year: Optional[int]`, which FastAPI 422s on `year=""` — exactly what an unselected `<select>` submits — because the existing tests called `browse_releases()` directly rather than hitting the route through the actual query-string path a browser sends; fixed by accepting `year` as a raw string and parsing manually, with a new regression test against the real route. Also discovered mid-session that `.claude/launch.json`'s port 8000 collided with the user's own long-running `uvicorn --reload` process from before a laptop restart; moved the agent's own preview port to 8001 rather than disturbing it. 21 net new/changed tests (156 total).
- *(2026-06-22)* Fixed: pressing Enter in the search box was clearing the search instead of keeping results. Cause: the `#controls` form has `hx-get="/search"`, but its explicit `hx-trigger` didn't list `"submit"` — an explicit `hx-trigger` *replaces* htmx's default trigger for an element rather than adding to it, so htmx stopped intercepting the form's native submit event entirely. Pressing Enter fell through to a real browser form submission — a full-page GET to `/` (no `action=` set, so it defaults to the current URL), which ignores `q`/`year`/`genre`/`artist` and re-renders the unfiltered browse list, looking exactly like the search getting cleared. Fixed by adding `submit` to the `hx-trigger` list. Verified live via `form.requestSubmit()` (same native-submit path Enter takes): confirmed via network log that it now fires the htmx `/search` AJAX call with no `GET /` page reload, and `window.location.href` stays at `/`. 1 new regression test (157 total).
- *(2026-06-22)* Added loading feedback to the Sync/Enrich buttons (`hx-disabled-elt` + `hx-indicator`, spinner + "Syncing…/Enriching…" text) — they were doing real work the whole time but with zero visual indication, so a 60s+ real sync just looked frozen. Verified live: triggered a real enrich run, confirmed via DOM inspection that the button disables immediately and the indicator's opacity reaches 1 (had to check after the 150ms CSS transition settles, not immediately on trigger). While verifying, noticed the live 237-track enrich run against the real collection took several minutes rather than the ~50s estimated from the earlier 348-track run — `enrich/sources/getsongbpm.py` calls `httpx.get()` directly per lookup with no persistent client/connection reuse, so each of the 237 sequential requests pays fresh TCP/TLS setup; left running in the background rather than killed, since `enrich_unmatched_tracks()` only commits once at the end (killing it would have just discarded that run's progress, not corrupted anything). Worth a connection-pooling fix later if enrichment speed becomes a real annoyance. 1 new test (158 total).
- *(2026-06-22)* Benchmarked the connection-pooling idea before committing to it: a standalone script timing 20 real tracks both ways (bare `httpx.get()` per call vs. one reused `httpx.Client()`) measured ~173ms/request unpooled vs ~68ms/request pooled — 2.5x faster, projecting ~41s vs ~16s for the full 237-track backlog. (The multi-minute live run from the previous entry doesn't match either number — almost certainly the headless preview-browser tab getting throttled/backgrounded during idle stretches between tool calls, not a true reflection of server processing speed; stopped that stale background request before benchmarking to avoid contaminating the measurement.) Implemented the fix: `enrich/sources/getsongbpm.py` now lazily creates one module-level `httpx.Client` and reuses it across every `lookup()` call instead of opening a fresh connection each time. Re-verified against 20 *different* real tracks through the actual fixed `lookup()` function (not the standalone benchmark script): 77ms/request, matching the benchmark's pooled number. Tests rewritten to patch `getsongbpm._get_client` (returning a fake client) instead of `httpx.get` directly, plus a new test asserting repeated `lookup()` calls reuse the identical client instance. 159 total.
