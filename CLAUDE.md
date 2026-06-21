# CLAUDE.md

Guidance for Claude when working in this repo.

## What this project is

A local-first tool to look up BPM and key for vinyl records the user owns, sourced from their Discogs collection plus BPM/key APIs (Beatport primary, GetSongBPM fallback, local audio analysis as a last resort for records no database covers). Used live while DJing at home — search a record, get its BPM/key instantly. See [docs/ARCHITECTURE_TARGET.md](docs/ARCHITECTURE_TARGET.md) for the full picture.

## Planning docs — read before making changes, update after

This repo has four living planning docs. At the start of any non-trivial task, check whether it touches them:

- [docs/ROADMAP.md](docs/ROADMAP.md) — phased build plan. Check items off as they land.
- [docs/ARCHITECTURE_CURRENT.md](docs/ARCHITECTURE_CURRENT.md) — what's actually built right now. Must always match reality.
- [docs/ARCHITECTURE_TARGET.md](docs/ARCHITECTURE_TARGET.md) — what the system should look like when done.
- [docs/DECISIONS.md](docs/DECISIONS.md) — ADR-style log of architectural choices and why they were made.

**Rule: if a conversation or change touches something one of these docs describes, update the doc in the same turn — don't leave it stale.** Concretely:

- Finished a roadmap item (e.g. built the Discogs sync, shipped the search UI)? Check it off in `ROADMAP.md` **and** add/update the relevant entry in `ARCHITECTURE_CURRENT.md`'s update log so it stops saying "doesn't exist."
- Built something not on the roadmap, or built it differently than `ARCHITECTURE_TARGET.md` describes? Update `ARCHITECTURE_TARGET.md` to match reality, and add a `DECISIONS.md` entry explaining why the plan changed (don't just edit silently — a future session needs the *why*, not just the *what*).
- Made a real architectural choice in conversation (new dependency, changed data source priority, changed the data model, picked a different framework, reversed an ADR) — even if no code was written yet? Add an ADR entry to `DECISIONS.md`. Use the existing entries as the format template: Status, Decision, Why, Implications (and "Open risk" if relevant).
- About to start implementation work and the plan in these docs is unclear or contradicts what's being asked? Resolve the contradiction in the docs first (or ask the user), don't silently build something that diverges from the written plan.

`ARCHITECTURE_CURRENT.md` is the one most likely to silently rot — it's easy to ship code and forget to mark it as real. Treat "the docs are stale" as a bug, the same way you'd treat a failing test.

## Stack reminders (see DECISIONS.md for full rationale)

- Python, FastAPI, SQLite. No Node build step — frontend is Jinja2 + htmx.
- Local-first: no cloud hosting, no multi-user auth, bound to localhost/LAN.
- BPM/key data is tiered: Beatport → GetSongBPM → local audio analysis → manual entry, with `source` provenance always stored. Never let automated enrichment overwrite a `manual` value.
- Discogs sync is pull/cache into SQLite, not live-per-search. Search must work instantly and offline against local data.

## Known open risk

Beatport API access is partner-gated, not self-serve — approval is not guaranteed. Until confirmed, treat GetSongBPM as the practical primary source and don't assume Beatport-level coverage. Check `docs/ROADMAP.md` Phase 0 and `docs/DECISIONS.md` ADR-003 for current status before relying on Beatport in new work.
