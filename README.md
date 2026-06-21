# Vinyl DJ Library

A local app that looks up the BPM and key for vinyl records you own, so you can search your collection while DJing and instantly see the numbers you need to beatmatch — no more guessing or digging through old notes.

It works by:
1. Pulling your collection from your **Discogs** account (the free record-cataloging/marketplace site most vinyl DJs already use — this assumes your records are added to your Discogs collection already).
2. Looking up BPM/key for each track automatically via **GetSongBPM.com**'s free database.
3. Letting you fill in anything it can't find by hand — either type a number you already know, or use the built-in **tap-tempo counter** to get a real BPM by tapping along to the beat.

Everything runs locally on your own machine. Your collection and listening data never leave your computer except to talk directly to Discogs/GetSongBPM.

## Quick start

You'll need a Mac or PC with Python 3.9 or newer. Most Macs already have this — open Terminal and run `python3 --version` to check. If you don't have it, get it from [python.org](https://www.python.org/downloads/).

1. **Download this project.** Either click the green **Code** button on GitHub → **Download ZIP** and unzip it, or if you're comfortable with git:
   ```bash
   git clone https://github.com/tants-dev/vinyl-dj-library.git
   ```
2. **Open a terminal in the project folder** and run:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e '.[dev]'
   ```
3. **Get your API keys** (see below), then copy the template and fill in your values:
   ```bash
   cp .env.example .env
   ```
   Open `.env` in any text editor and paste in your keys.
4. **Start the app:**
   ```bash
   uvicorn api.main:app --reload
   ```
   Then open <http://127.0.0.1:8000> in your browser.
5. Click **Sync Discogs** to pull in your collection, then **Enrich BPM/key** to look up tempos and keys automatically.

Each time you want to use it again, you only need step 4 (after running `source .venv/bin/activate` once per terminal session).

## Getting your API keys

You need two things, both free. `BEATPORT_*` in `.env` can stay blank — see the note below.

### Discogs

1. Log in and go to [discogs.com/settings/developers](https://www.discogs.com/settings/developers).
2. Click **Generate new token** and copy it.
3. In your `.env` file, set:
   - `DISCOGS_TOKEN` — the token you just copied
   - `DISCOGS_USERNAME` — your Discogs username
   - `DISCOGS_COLLECTION_FOLDER_ID` — leave as `0` to sync your whole collection

### GetSongBPM

1. Go to [getsongbpm.com/api](https://getsongbpm.com/api) and fill in the form.
2. It requires a **backlink** — a public webpage that links back to GetSongBPM. If you don't have your own site, you can use this project's GitHub page (`https://github.com/tants-dev/vinyl-dj-library`) — it's public and already credits GetSongBPM in the Credits section below.
3. They'll email you an API key. Set `GETSONGBPM_API_KEY` in your `.env` to that.

### Beatport (not usable yet)

Beatport would be the best source for electronic music specifically, but their API requires a partner application that isn't open to individual developers. Leave `BEATPORT_CLIENT_ID`/`BEATPORT_CLIENT_SECRET` blank — the app works fine without them, just with GetSongBPM as the only automatic source.

## Using the app

- **Search** — type an artist, title, label, or catalog number to find a record instantly.
- **Browse** — when the search box is empty, you'll see your whole collection, filterable by year/genre/artist.
- **Sync Discogs** — re-pulls your collection (run this again any time you buy new records).
- **Enrich BPM/key** — looks up BPM/key automatically for anything missing.
- **Tap BPM** (top-left, every page) — for records nothing could find data for, tap the button or press space along with the beat to get a real BPM, then type it into that record's entry by hand.
- **Quit** (top-right) — stops the server when you're done for the night.

## Test

```bash
pytest
```

## Stack

Python, FastAPI, SQLite (via SQLModel), Jinja2 + htmx (vendored locally, no CDN dependency, no JS build step). See [docs/DECISIONS.md](docs/DECISIONS.md) for the reasoning.

## Docs (for the curious, or for picking up development)

- [docs/ROADMAP.md](docs/ROADMAP.md) — phased build plan
- [docs/ARCHITECTURE_CURRENT.md](docs/ARCHITECTURE_CURRENT.md) — what's actually built
- [docs/ARCHITECTURE_TARGET.md](docs/ARCHITECTURE_TARGET.md) — system design
- [docs/DECISIONS.md](docs/DECISIONS.md) — why things are built the way they are
- [CLAUDE.md](CLAUDE.md) — rules for keeping the above in sync

## Credits

Track BPM/key data provided by [GetSongBPM.com](https://getsongbpm.com).
