# Vinyl DJ Library

A local-first tool to look up BPM and key for vinyl records you own. Syncs your collection from Discogs, enriches it with BPM/key data (Beatport, GetSongBPM, or local audio analysis as a last resort for white labels/promos), and gives you an instant offline search while you're DJing.

> **Status:** early skeleton. The app boots and the search/sync/enrich/manual-override flows work, but no real collection data or API credentials are wired in yet. See [docs/ARCHITECTURE_CURRENT.md](docs/ARCHITECTURE_CURRENT.md) for exactly what's real right now.

## Docs

- [docs/ROADMAP.md](docs/ROADMAP.md) — phased build plan
- [docs/ARCHITECTURE_CURRENT.md](docs/ARCHITECTURE_CURRENT.md) — what's actually built
- [docs/ARCHITECTURE_TARGET.md](docs/ARCHITECTURE_TARGET.md) — system design
- [docs/DECISIONS.md](docs/DECISIONS.md) — why things are built the way they are
- [CLAUDE.md](CLAUDE.md) — rules for keeping the above in sync

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # fill in DISCOGS_TOKEN etc. — see .env.example
```

## Run

```bash
uvicorn api.main:app --reload
```

Then open http://127.0.0.1:8000 — search bar on the left, BPM/key on the right.

## Test

```bash
pytest
```

## Stack

Python, FastAPI, SQLite (via SQLModel), Jinja2 + htmx (vendored locally, no CDN dependency, no JS build step). See [docs/DECISIONS.md](docs/DECISIONS.md) for the reasoning.

## Credits

Track BPM/key data provided by [GetSongBPM.com](https://getsongbpm.com).
