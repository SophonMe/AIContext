---
name: aicontext-canvas
description: >
  Produce a visual "canvas" (HTML card, image, etc.) from a user's AIContext
  personal history. Routes a natural-language request to a content usecase
  skill, then renders the resulting bundle with a chosen renderer skill.
---

# AIContext Canvas Skill

## What This Skill Does

Given a natural-language request like `/aicontext-canvas today in my history`,
you produce a single self-contained HTML file in the user's browser that
visualizes some slice of their personal history.

The work happens in two decoupled phases:

1. **Content curation** — a usecase skill under `usecases/` queries the
   user's AIContext database, fetches web/Chrome content when useful, and
   emits a content bundle JSON. Content skills never write HTML.
2. **Rendering** — a renderer skill under `renderers/` reads the bundle and
   produces the HTML. Renderer skills never query user data.

This separation lets us add new visual formats without touching content
logic, and new usecases without rewriting the card design.

## Workflow

1. **Parse the request.** The user's natural-language argument picks a
   usecase (e.g. "today in my history" → `usecases/today-in-history/`).
   If the intent is ambiguous, ask a single clarifying question. Never
   invent a usecase that doesn't exist.
2. **Create this run's directory.** Compute a local-time timestamp
   `<YYYY-MM-DD-HHMM>` and create
   `~/.aicontext/canvas/<usecase>/<YYYY-MM-DD-HHMM>/`. All outputs for
   this run — bundle, HTML, assets — live inside this folder. Pass this
   run directory path to the usecase and renderer skills.
3. **Run the usecase skill.** Follow the instructions in
   `usecases/<usecase>/SKILL.md`. It will produce a content bundle
   matching `protocol.md` and write it to
   `<run-dir>/.bundle.json`.
4. **Pick a renderer.** Read every `renderers/*/SKILL.md` frontmatter.
   Match the bundle shape and the user's stated preferences (if any — e.g.
   "polaroid style", "make it dark") against each renderer's `accepts`
   and `best_for`. Pick the narrowest fit. If nothing fits better,
   default to `canvas-card`.
5. **Run the renderer skill.** Follow the instructions in
   `renderers/<renderer>/SKILL.md`. It reads `<run-dir>/.bundle.json`
   and writes `<run-dir>/<slug>.html`.
6. **Open the file.** Open the HTML in the user's default browser
   (`open <path>` on macOS, `xdg-open <path>` on Linux).
7. **Leave the run folder in place.** Do not delete `.bundle.json` or the
   HTML. Each run's folder is self-contained, so previous runs are never
   overwritten, and the agent can re-render the same bundle with a
   different renderer (writing a sibling `<slug>.html` in the same run
   folder) without re-querying data.

## Decisions the Agent Makes

- **Which usecase.** Match the user's phrase to a folder under `usecases/`.
  Prefer stem-matching words ("history", "today", "trip"). If the match
  is weak, ask; do not guess silently.
- **Which renderer.** You decide freely based on:
  - Bundle shape (required fields present/absent).
  - Renderer frontmatter (`accepts`, `best_for`, `not_for`).
  - Any visual cues in the user's prompt ("polaroid", "dark", "minimal").
  - Default to `canvas-card` when no signal points elsewhere.
- **Content vs render boundary.** If you find yourself writing HTML in a
  usecase skill, stop — that belongs in a renderer. If you find yourself
  querying the database from a renderer, stop — that belongs in a usecase.

## Output Layout

```
~/.aicontext/canvas/
├── today-in-history/
│   ├── 2026-04-17-1830/
│   │   ├── .bundle.json
│   │   ├── 2019-sf-arrival.html
│   │   └── assets/
│   │       └── 2019-sf-arrival/
│   ├── 2026-04-17-1945/
│   │   ├── .bundle.json
│   │   └── 2021-skagit-tulips.html
│   └── ...
└── <other-usecase>/
    └── ...
```

Each run gets its own timestamped folder, so repeated runs of the same
usecase never silently overwrite earlier outputs. The bundle, HTML, and
any per-run assets live together inside that folder.

## Important Rules

- **Never modify** files under the installed skill tree. All generated
  output goes under `~/.aicontext/canvas/`.
- **HTML must work from `file://`** — no external script/style URLs at
  runtime. Inline everything the renderer needs.
- **No multi-modal generation.** Text, HTML, and CSS only. Images are
  allowed when pulled from the user's Chrome or an explicit web fetch,
  but skills do not generate images.
- **One-shot execution.** The usecase and renderer skills should both
  complete without asking the user questions. Only the meta-skill asks
  questions, and only when the usecase is genuinely ambiguous.

## Files

- `protocol.md` — content bundle schema and renderer selection rules
- `usecases/<name>/SKILL.md` — one per content usecase
- `renderers/<name>/SKILL.md` — one per visual format
