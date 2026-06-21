# Architecture Decisions

ADR-style log of choices made for the vinyl DJ library tool, and why. Newest at the bottom. Don't rewrite history here — if a decision is reversed, add a new entry that supersedes it and mark the old one superseded.

---

## ADR-001: Local-first, single-user, no cloud hosting

**Status:** Accepted

**Decision:** The app runs entirely on the user's own machine (or home network). No cloud deployment, no multi-tenant auth, no hosted database.

**Why:** This is a personal vinyl collection lookup tool used while DJing at home. There's exactly one user. Cloud hosting would add deployment, auth, and ops complexity with zero benefit — it would also mean collection data and API keys live somewhere outside the user's control for no reason.

**Implications:** No need for user accounts, sessions, or a production deployment story. Local web server bound to localhost/LAN is sufficient. Backups are the user's own responsibility (e.g. commit the SQLite file, or periodic copy).

---

## ADR-002: Python + FastAPI + SQLite as the core stack

**Status:** Accepted

**Decision:** Backend and sync/enrichment scripts are Python. Web API is FastAPI. Local storage is a single SQLite file.

**Why:** User has no strong stack preference but picked Python. Python has mature clients for Discogs, easy HTTP for the BPM APIs, and (if local audio analysis is ever added, see ADR-003) the best ecosystem for that (`librosa`, `essentia`, `aubio`). FastAPI is lightweight, has good async support for calling external APIs without blocking, and needs no separate build toolchain. SQLite needs zero setup/ops for a single-user local app and is trivially backed up as one file.

**Implications:** No Node/JS build step required. Frontend will be server-rendered (Jinja2) plus light JS/htmx rather than a full SPA framework, to keep the whole stack in one language and avoid a frontend build pipeline.

---

## ADR-003: Tiered BPM/key data strategy — Beatport primary, GetSongBPM fallback, local audio analysis last resort, manual override always available

**Status:** Accepted (with a known open risk — see below)

**Decision:** When enriching a track with BPM/key, try sources in this order and stop at the first hit:
1. **Beatport API** — best coverage and accuracy for electronic music specifically, which is most of what this tool is for.
2. **GetSongBPM.com API** — open, self-serve API key, decent general coverage, used when Beatport has no match or isn't accessible.
3. **Local audio analysis** — if the user records a short needle-drop sample (mic/line-in capture), run it through `librosa`/`essentia` to estimate BPM and key directly from audio.
4. **Manual entry** — the user can always type in or correct BPM/key by hand; this is stored as a distinct "manual" source and is never overwritten by automated re-enrichment.

Every stored BPM/key value keeps a `source` field (`beatport` / `getsongbpm` / `local_analysis` / `manual`) so the UI can show provenance and so re-running enrichment doesn't clobber manual corrections.

**Why:** Beatport is the gold standard for electronic music BPM/key data, which matters because most of what gets bought on vinyl by electronic DJs is exactly the kind of release Beatport catalogs well. But **Beatport's API is partner-gated, not open self-serve** — there's no guarantee of approval, and even if approved there may be usage restrictions. GetSongBPM is a safe, genuinely open fallback with no approval gate, though its coverage skews more mainstream/pop and will miss a lot of niche electronic vinyl. Crucially, vinyl-only DJ collections routinely include **white labels, promos, dubplates, and bootlegs that exist in no metadata database at all** — for those, the only option is analyzing the actual audio, which means a local-analysis path is a real feature need here, not a nice-to-have.

**Open risk:** Beatport API partner access is not guaranteed. Until/unless that access is obtained, GetSongBPM becomes the de facto primary source and coverage expectations should be set accordingly. Revisit this ADR once Beatport access is confirmed approved or denied.

---

## ADR-004: Local web app (FastAPI + browser UI) over CLI or Electron

**Status:** Accepted

**Decision:** The DJing-time interface is a local web app — FastAPI backend serving a simple search page — rather than a terminal tool or a packaged Electron/Tauri desktop app.

**Why:** A web UI on localhost works from any device on the home network (laptop, tablet propped up near the decks, phone) without needing a native app build per platform. It's visually friendlier for fast record lookups (cover art, sortable BPM/key columns) than a CLI, and far less build/packaging complexity than Electron. Since this is local-first (ADR-001) there's no real downside to "it's a web page" — there's no actual network exposure concern beyond the home LAN.

**Implications:** Needs a `uvicorn` (or similar) process running locally before use. A future stretch goal could add a system-tray launcher or a basic PWA manifest for an app-like feel on a tablet, but that's not in scope for the initial build.

---

## ADR-005: Discogs collection sync is pull/cache, not live-per-search

**Status:** Accepted

**Decision:** The user's Discogs collection is synced into the local SQLite DB periodically (manually triggered, e.g. `sync` command/button), not queried live from Discogs on every search.

**Why:** Discogs enforces API rate limits (60 req/min authenticated) and the collection doesn't change every time the user wants to look up a record while DJing. Searching must be instant and work offline; hitting Discogs live per search would be slow, rate-limit-prone, and pointless since collection data changes rarely (only when buying/selling records).

**Implications:** Need a "last synced" indicator and a manual re-sync action. Enrichment (BPM/key lookups) runs against newly-synced/unenriched tracks, not on every search either.
