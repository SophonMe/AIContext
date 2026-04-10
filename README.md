# AIContext

[![CI](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml/badge.svg)](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sophonme-aicontext)](https://pypi.org/project/sophonme-aicontext/)

**Local-first AI context engine.** Your Claude Code or Codex agent automatically pulls from your local data — coding sessions, browser history, AI conversations — before asking you for context.

No cloud. No uploads. Everything stays on your machine.

## Install

```bash
pip install sophonme-aicontext && aicontext install
```

`aicontext install` scans your machine for supported data sources, asks for consent per source type, ingests the data into a local SQLite database, and installs agents for Claude Code, Codex, and Pi.

```
Scanning for local data sources...

  [found] Claude Code sessions
          /Users/you/.claude/projects
         Include? [Y/n] y
          -> included

  [found] Chrome browser history
          /Users/you/Library/Application Support/Google/Chrome/Default/History
         Include? [Y/n] y
          -> included

Ingesting data...
  Ingested: 24803 new records, 0 updated

Done.

The sophonme-context-engine agent is now active in Claude Code.
The Codex agent is installed at `~/.codex/agents/sophonme-context-engine.toml`.
Your data syncs automatically every hour.
```

If you use Codex, older app versions may need this in `~/.codex/config.toml` for spawned-subagent support:

```toml
[features]
multi_agent = true
```

If your Codex build already supports spawned agents by default, you do not need this. Restart Codex after changing the config.

## How it works

After install, Claude Code and Codex both have a `sophonme-context-engine` agent. The agent queries your local activity database to surface relevant history for whatever task you're working on.

A background sync service (`launchd` on macOS) re-ingests your data every hour, so context stays fresh without any manual steps.

```
~/.aicontext/
 ├── SKILL.md
 ├── data/
 │   ├── activity.db       — unified timeline
 │   └── reference_data/   — full session content
 ├── reference/            — per-source schema docs
 └── scripts/
     └── query.py          — read-only SQL query tool
```

The agent reads from `~/.aicontext/` using a read-only SQL query script. It never writes to your data, and never sends anything outside your machine.

## Supported sources

| Source | Data |
|--------|------|
| Claude Code | Session history, prompts, project paths |
| Codex | Session history, prompts |
| Chrome | Browser visits, downloads |
| Edge | Browser visits, downloads |
| Safari | Browser visits |

More sources coming soon.

## Supported agents

| Agent | Status |
|-------|--------|
| Claude Code | Supported |
| Codex | Supported (older versions may need `multi_agent = true` for spawned subagents) |
| Pi | Supported |

## Privacy

All data is stored locally at `~/.aicontext/`. Nothing is sent to any server. The agent only reads from this directory.

## Contributing

Contributions are welcome — new data sources are the most impactful place to start.

Each source is a single file in `aicontext/sources/` that implements two methods: `ingest_activity()` returns a list of `ActivityRecord`, and `ingest_reference()` returns full session content. See `sources/claude_code.py` as a reference.

Ideas for new sources: Firefox, Arc, VS Code history, Obsidian, Zotero, Spotify, shell history.

If this project is useful to you, consider giving it a star — it helps others find it.

[![GitHub stars](https://img.shields.io/github/stars/SophonMe/AIContext?style=social)](https://github.com/SophonMe/AIContext)
