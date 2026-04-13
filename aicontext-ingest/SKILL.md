---
name: aicontext-ingest
description: >
  Implement data source ingestion for AIContext. Explore a user's data export,
  identify ingestible sources, and write DataSource classes to parse them.
---

# AIContext Data Ingestion Skill

## What This Skill Does

Given a base data path from the user, you explore the directory, identify
ingestible data sources, and implement DataSource classes that parse them
into AIContext's unified activity database.

## Exploring the AIContext Source Code

You are encouraged to read the actual aicontext source code for deeper
understanding beyond what `protocol.md` covers. To find the installed
package location:

```bash
python3 -c "import aicontext; import os; print(os.path.dirname(aicontext.__file__))"
```

Key files worth reading:
- `sources/base.py` -- the DataSource ABC you're implementing against
- `records.py` -- ActivityRecord and ReferenceFile dataclasses
- `timestamps.py` -- timestamp parsing helpers you can import
- `ingester.py` -- how ingestion, validation, and dedup work
- `sources/` -- existing built-in sources as reference implementations

## Workflow

1. Read `protocol.md` to understand the DataSource interface and conventions
2. Explore the user-provided base path to discover what data is present
3. Match discoveries against guides in `sources/` for known formats
4. **Ask the user to confirm** which sources to ingest and the exact paths
5. Read the relevant guide(s) in `sources/<name>.md`
6. Examine the actual data files to understand the exact format
7. Implement DataSource class(es) in `~/.aicontext/data_sources/<source_key>.py`
8. Add entries to `~/.aicontext/config.json`
9. Tell the user to run `aicontext sync` to ingest

The base path doesn't necessarily contain all known source types. Only
implement sources for data that actually exists.

Each data source is fully independent — its own guide, data files, and output
file — so exploration and implementation can be parallelized. When there are
many sources to implement, prefer doing file exploration, data examination,
and code writing in parallel rather than sequentially.

If you discover useful ingestible data that doesn't match any existing guide
in `sources/`, ask the user to confirm, then:
1. Implement the DataSource code regardless
2. Try to write a new `.md` guide to the **repo source** of this skill (find
   it via `python3 -c "import aicontext; ..."` — the `aicontext-ingest/`
   directory is a sibling of the `aicontext/` package). If the repo source
   is not available or not writable, skip the guide -- the code is what matters.

## Important Rules

- **Only write code to `~/.aicontext/data_sources/`** -- never modify files under `aicontext/`
- **Ask the user to confirm** discovered data sources and paths
- **Do NOT ask implementation questions** -- the user doesn't know AIContext
  internals. Use the guides and actual data to make all implementation decisions yourself.
- **No multi-modal data** -- only ingest text and structured data (CSV, JSON, HTML,
  SQLite, ICS, etc.). Skip images, audio, video, and binary files.
- **No defensive fallbacks** -- if a record's action type, timestamp, or title
  cannot be determined from the data, skip it. Do not invent fallback values.

## What Data To Ingest

Timestamped user activity/events:
- Purchases, orders, cart additions
- Search queries, browsing history
- Messages, conversations (AI or human)
- Calendar events, meetings
- Media consumption (watch/listen history)
- App usage, downloads

Each record represents one discrete user action at a point in time, with:
- A clear vendor/platform (`source`)
- A specific product/feature (`service`)
- A past-tense verb describing the action (`action`)
- Human-readable content (`title`)

NOT suitable for ingestion: raw binary files, credentials, data without
timestamps, large unstructured blobs, system logs, configuration files.

## Registering in config.json

After implementing, read `~/.aicontext/config.json` and append an entry to
the `"sources"` array:

```json
{"key": "<source_key>", "path": "<confirmed_path>", "mode": "static"}
```

Use `"mode": "static"` for one-time data exports (Google Takeout, Amazon CSV, etc.).
Use `"mode": "dynamic"` for data that updates continuously (e.g., a local app database).

## Files

- `protocol.md` -- Interface contract, field conventions, data consistency, coding rules
- `sources/` -- Per-data-source format guides (one `.md` per data source type)
