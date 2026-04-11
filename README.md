# AIContext

[![CI](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml/badge.svg)](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sophonme-aicontext)](https://pypi.org/project/sophonme-aicontext/)

**The personal context layer for AI agents.**

Local-first, private by default, and built to help agents start from your real context — not a blank slate.

`aicontext` gives agents access to relevant personal context from your own data: coding sessions, browser history, AI conversations, and exported archives. Instead of asking you to repeatedly reconstruct what you were doing, the agent can recover the surrounding thread itself.

This is not just memory for chatbots.
It is a system for ingesting, normalizing, and querying the artifacts of your digital life so agents can better understand what a task is connected to: what you worked on, what you looked at, what you already tried, and what may matter now.

Everything stays under your control. Data is ingested locally, stored locally, and queried locally. No cloud sync, no uploads, no external storage.

## Install

```bash
pip install sophonme-aicontext && aicontext install
```

`aicontext` install scans your machine for supported local data sources, asks for consent before including each source type, ingests approved data into a local SQLite database, and installs the local agent configuration used by supported tools such as Claude Code, Codex, and Pi.

It does not upload your data or require any cloud service. Changes are limited to local configuration and the `~/.aicontext/` directory, and everything can be removed later if you uninstall the tool.

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
Your data ingests automatically every hour.
```

## Example Prompts

```
foo
```

## How it works

After install, Claude Code and Codex both have a `sophonme-context-engine` agent. The agent queries your local activity database to surface relevant context for whatever task you're working on.

A background periodic local ingest service (`launchd` on macOS) re-ingests your data every hour, so context stays fresh without any manual steps.

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

| Agent | Status | Type |
|-------|--------|--------|
| Claude Code | Supported | Subagent |
| Codex | Supported (older versions may need `multi_agent = true` for spawned subagents) | Subagent |
| Pi | Supported | Skill |
| OpenClaw | Supported | Skill |

### Troubleshooting
If you use Codex, older app versions may need this in `~/.codex/config.toml` for spawned-subagent support:

```toml
[features]
multi_agent = true
```

If your Codex build already supports spawned agents by default, you do not need this. Restart Codex after changing the config.

## Privacy

All data is stored locally at `~/.aicontext/`. Nothing is sent to any server. The agent only reads from this directory.

## Contributing

Contributions are welcome, especially new data sources.

The easiest way to contribute is to add a new source under `aicontext/sources/`. Each source is a single file that implements two methods: `ingest_activity()` for timeline records and `ingest_reference()` for full session content. See `sources/claude_code.py` for the smallest complete example.

Good source ideas include Firefox, Arc, VS Code history, Obsidian, Zotero, Spotify, and shell history.

If you want feedback before building, open an issue with the source you have in mind and any notes on the schema or data shape. That makes it easier to align on fit before you start.

If this project is useful to you, consider giving it a star — it helps more people find it.

[![GitHub stars](https://img.shields.io/github/stars/SophonMe/AIContext?style=social)](https://github.com/SophonMe/AIContext)
