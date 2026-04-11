# AIContext

[![CI](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml/badge.svg)](https://github.com/SophonMe/AIContext/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sophonme-aicontext)](https://pypi.org/project/sophonme-aicontext/)

**The personal context layer for AI agents.**

Local-first, private by default, and built to help agents start from your real context — not a blank slate.

`aicontext` gives agents access to relevant personal context from your own data: coding sessions, browser history, AI conversations, and exported archives. Instead of asking you to repeatedly reconstruct what you were doing, the agent can recover the surrounding thread itself. Recent activity and long-term history combine across sources to surface not just what you did, but who you are: your skills, your curiosities, your habits, and where your attention is going next.

This is not just memory for chatbots.
It is a system for ingesting, normalizing, and querying the artifacts of your digital life so agents can better understand what a task is connected to: what you worked on, what you looked at, what you already tried, and what may matter now.

Everything stays under your control. Data is ingested locally, stored locally, and queried locally. No cloud sync, no uploads, no external storage.

## Install

```bash
pip install sophonme-aicontext && aicontext install
```

`aicontext install` scans your machine for supported local data sources, asks for consent before including each source type, ingests approved data into a local SQLite database, and installs the local agent configuration used by supported tools such as Claude Code, Codex, Pi, and OpenClaw.

It does not upload your data or require any cloud service. Changes are limited to local configuration and the `~/.aicontext/` directory, and everything can be removed later with `aicontext uninstall`.

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

  Source              Parsed    New  Updated
  ──────────────────────────────────────────
  Claude Code         12,847  12,847        0
  Chrome               8,456   8,456        0
  ──────────────────────────────────────────
  Total               21,303  21,303        0

  Generated SKILL.md  -> ~/.aicontext/skill/SKILL.md
  Claude Code agent   -> ~/.claude/agents/sophonme-context-engine.md
  Codex agent         -> ~/.codex/agents/sophonme-context-engine.toml
  Pi / OpenClaw skill -> ~/.agents/skills/personal-data
  Background sync     -> hourly via launchd (sophonme.aicontext)

Done. The sophonme-context-engine agent is now active in Claude Code, Codex, Pi, and OpenClaw.
```

## Example Prompts

```
"Do thorough research on my history, and infer my MBTI"
"Recommend a book, video, or podcast for me"
"What do I want to buy the most?"
"Show how deeply you know about me"
"Check my history and suggest what I should do this weekend"
"What is the biggest miss of my daily life that I may not even be aware of?"
```

## How it works

After install, Claude Code and Codex both have a `sophonme-context-engine` agent. The agent queries your local activity database to surface relevant context for whatever task you're working on.

A background periodic local ingest service (`launchd` on macOS) re-ingests your data every hour, so context stays fresh without any manual steps.

```
~/.aicontext/
 ├── data/
 │   ├── activity.db       — unified timeline
 │   └── reference_data/   — full session content
 └── skill/
     ├── SKILL.md
     ├── reference/        — per-source schema docs
     └── scripts/
         └── query.py      — read-only SQL query tool
```

The agent reads from `~/.aicontext/` using a read-only SQL query script. It never writes to your data, and never sends anything outside your machine.

## Supported sources

| Source | Data |
|--------|------|
| Claude Code | Session history, prompts, project paths |
| Codex | Session history, prompts |
| Chrome | Browser visits, downloads |
| Edge | Browser visits, downloads |
| Dia | Browser visits, downloads |
| Safari | Browser visits |

More sources coming soon.

## Supported agents

| Agent | Type |
|-------|------|
| Claude Code | Subagent |
| Codex | Subagent |
| Pi | Skill |
| OpenClaw | Skill |

### Troubleshooting
If you use Codex, older app versions may need this in `~/.codex/config.toml` for spawned-subagent support:

```toml
[features]
multi_agent = true
```

If your Codex build already supports spawned agents by default, you do not need this. Restart Codex after changing the config.

## Privacy

All data is stored locally at `~/.aicontext/`. Nothing is sent to any server. The agent only reads from this directory.

However, when an agent queries your data, the results become part of the prompt sent to the model provider (Anthropic, OpenAI, etc.). This means fragments of your personal history may reach the provider's API. Choose a provider you trust, and consider disabling model training on your data to avoid your personal context being used to improve future models:

- [Anthropic (Claude)](https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training)
- [OpenAI](https://help.openai.com/en/articles/8983130-what-if-i-want-to-keep-my-history-on-but-disable-model-training)

## Contributing

Contributions are welcome, especially new data sources.

The easiest way to contribute is to add a new source under `aicontext/sources/`. Each source is a single file that implements two methods: `ingest_activity()` for timeline records and `ingest_reference()` for full session content. See `sources/claude_code.py` for the smallest complete example.

Good source ideas include Firefox, Arc, Obsidian, Zotero, Spotify, and shell history.

If you want feedback before building, open an issue with the source you have in mind and any notes on the schema or data shape. That makes it easier to align on fit before you start.

If this project is useful to you, consider giving it a star — it helps more people find it.

[![GitHub stars](https://img.shields.io/github/stars/SophonMe/AIContext?style=social)](https://github.com/SophonMe/AIContext)
