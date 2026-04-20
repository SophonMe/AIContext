# Canvas Protocol

This document defines the contract between **usecase skills** (content
curation) and **renderer skills** (HTML output). The meta-skill enforces
this contract.

## Content Bundle

Every usecase skill produces a single JSON file at:

```
~/.aicontext/canvas/<usecase>/<YYYY-MM-DD-HHMM>/.bundle.json
```

Each run gets its own timestamped subdirectory (local time). The bundle, the
rendered HTML, and any sibling assets for that run all live inside it.

The bundle is a JSON object with this shape:

```jsonc
{
  "usecase": "today-in-history",     // required — folder name
  "slug": "2019-san-francisco",      // required — short filesystem-safe id
  "title": "...",                    // required — primary headline text
  "body": "...",                     // required — main content (plain text
                                     //            or light markdown; single
                                     //            paragraph preferred)
  "meta": {                          // optional — short structured facts
    "date_today": "2026-04-17",      //            shown in small type
    "location": "San Francisco",
    "year": 2019
  },
  "accent_phrases": ["..."],         // optional — phrases to italicize in body
  "glosses": [                       // optional — inline foreign-word glosses
    {"term": "小麻雀", "gloss": "little sparrow"}
  ],
  "images": [                        // optional — base64 or local file paths
    {"path": "assets/foo.png", "alt": "..."}
  ],
  "extras": {                        // optional — renderer-specific freeform
    "tone": "quiet",
    "palette_hint": "paper"
  },
  "hints": {                         // optional — signals to the renderer
    "preferred_variant": null,       //            picker, never hard rules
    "avoid": []
  }
}
```

### Required fields

- `usecase`, `slug`, `title`, `body`.

A bundle without all four is invalid and must be rejected by the meta-skill
before any renderer runs.

### Optional fields

- `meta`, `accent_phrases`, `glosses`, `images`, `extras`, `hints`.
- Any field a renderer doesn't understand is silently ignored.

## Renderer Frontmatter

Every renderer SKILL.md begins with YAML frontmatter that tells the meta-skill
how and when to pick it:

```yaml
---
name: canvas-card
description: >
  Editorial paper-toned card with serif headline and short body. Best for
  intimate, reflective, single-paragraph content.
accepts:
  required: [usecase, slug, title, body]
  optional: [meta, accent_phrases, glosses, images]
best_for:
  - single-paragraph reflective narratives
  - dated "on this day" arcs
  - quoted personal writing
not_for:
  - long-form articles (> ~400 words)
  - tabular data
  - timelines spanning many dates
---
```

## Renderer Selection Rules

The meta-skill picks a renderer using, in order:

1. **Required-field fit.** Skip any renderer whose `accepts.required` is not
   a subset of the bundle's populated fields.
2. **User prompt signal.** If the user's prompt mentions a visual hint
   ("polaroid", "dark", "minimal"), prefer renderers whose name,
   description, or `best_for` matches.
3. **Usecase hint.** If `bundle.hints.preferred_variant` is set and points
   at a valid renderer, prefer it.
4. **Best-for fit.** Prefer the renderer whose `best_for` most specifically
   describes the bundle's shape and tone.
5. **Default.** Fall back to `canvas-card`.

Never pick a renderer listed in `bundle.hints.avoid` unless no other choice
exists.

## Data Access for Usecase Skills

- **Preferred**: run queries through `~/.aicontext/skill/scripts/query.py`.
  It is the same helper used by the sophonme-context-engine agent and gives
  consistent, well-validated results across sources.
- **Allowed**: read `~/.aicontext/data/activity.db` directly via `sqlite3`
  when the helper doesn't expose what you need. Do not write to the DB.
- **External content**: web pages via the agent's WebFetch tool; active
  browser content via the agent's Chrome tool. Save retrieved images under
  the current run's `assets/<slug>/` subdirectory and reference them from
  the bundle via relative `path`.

## File Conventions

- Each run lives in its own timestamped subdirectory:
  `~/.aicontext/canvas/<usecase>/<YYYY-MM-DD-HHMM>/`.
- Output HTML name inside that folder: `<slug>.html`.
- Bundle: `.bundle.json` in the same folder.
- Assets: `assets/<slug>/` in the same folder.
- HTML must be self-contained: inline CSS, inline JS, base64-embedded small
  images. The file must open correctly from `file://`.
- Assets larger than ~1 MB may be kept as sibling files under
  `assets/<slug>/` and referenced with relative paths. The renderer decides
  which to inline.
