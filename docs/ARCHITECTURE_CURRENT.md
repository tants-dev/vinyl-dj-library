# Current Architecture

What actually exists in this repo right now. Unlike [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md), this file describes reality, not intent — it should always match the state of the code. See [CLAUDE.md](../CLAUDE.md) for the rule that keeps it that way.

## Status: greenfield — planning only

No application code exists yet. This repo currently contains only:

```
vinyl-dj-library/
  CLAUDE.md
  docs/
    ROADMAP.md
    ARCHITECTURE_CURRENT.md   (this file)
    ARCHITECTURE_TARGET.md
    DECISIONS.md
```

Nothing has been built: no Discogs sync, no enrichment pipeline, no database, no API, no UI. No API credentials have been provisioned (Discogs token, GetSongBPM key, Beatport partner application) as of the time this doc was written.

## What's actually decided so far

The architectural decisions in [DECISIONS.md](DECISIONS.md) (stack, data sources, sync model) are settled, but none are implemented. Treat this file as the single source of truth for "is X actually built" — if [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md) describes a component, assume it doesn't exist until this file says it does.

## Update log

This section should grow as implementation proceeds — each phase of [ROADMAP.md](ROADMAP.md) that lands should get an entry here describing what's now real, replacing the "nothing has been built" statement above piece by piece.

- *(2026-06-21)* Repo created with planning docs only. No code.
