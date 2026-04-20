---
name: canvas-renderer-card
description: >
  Editorial card renderer — paper-toned card on a dark page, serif type,
  one accent color, generous whitespace, one hairline rule. The default
  renderer for aicontext-canvas. Works for a wide range of short-to-medium
  text-first content: narratives, summaries, lists, quotes, highlights,
  recaps, memos. Body length and structure flex with the bundle.
accepts:
  required: [usecase, slug, title, body]
  optional: [meta, accent_phrases, glosses, images, extras]
best_for:
  - text-first share cards meant to be screenshotted
  - single-paragraph narratives
  - short structured content (2–6 bullets, a pull quote, a small list)
  - recaps, digests, highlights, memos
not_for:
  - long-form articles (more than ~600 words of body text)
  - content that is fundamentally tabular (use a table renderer)
  - content that needs interactive controls beyond light editing
  - multi-image galleries where images are the primary content
---

# Canvas Card Renderer

You are invoked by the `aicontext-canvas` meta-skill after a usecase skill
has written a content bundle inside a per-run directory:

```
~/.aicontext/canvas/<usecase>/<YYYY-MM-DD-HHMM>/.bundle.json
```

The meta-skill passes you that run directory as `<run-dir>`. Your job is
to render the bundle as a single self-contained HTML file in the same
folder. You are the default renderer — usecases will pass you a wide
variety of content shapes, and you must adapt without breaking the visual
identity.

## Output

Write to:

```
<run-dir>/<slug>.html
```

`<slug>` comes from the bundle. The per-run timestamp is already encoded
in the folder name, so do not add one to the filename.

The file must work from `file://` — inline the CSS, inline the JS, base64
any small images embedded from the bundle.

## Body Shapes You Must Handle

`bundle.body` is plain text or light markdown. It may be any of:

- A single flowing paragraph.
- Multiple short paragraphs separated by blank lines.
- A short markdown list (`- item` or `1. item`).
- A pull quote (`> ...`).
- A small mixture of the above.

Render markdown minimally: paragraphs, unordered and ordered lists, block
quotes, inline `*italic*` / `_italic_` / `**bold**`, and inline code.
Do not attempt to render headings (`#`), tables, or code blocks — if the
body contains them, treat them as plain text and let the meta-skill pick a
different renderer next time. Do not introduce visual elements the bundle
did not ask for.

## Visual Identity (invariant across content shapes)

Keep these constant so every card feels like part of the same family:

- Dark page background; cream-paper card centered on the page.
- Dark ink body; exactly one accent color (warm ochre by default).
- Serif typography for title and body; monospace for meta and footer mark.
- One hairline rule, placed between the footer mark and the body.
- Generous whitespace; reading column around 56ch.
- Card height is content-driven — no forced aspect ratio that crushes or
  pads the text. Short bodies produce short cards; longer bodies grow.

Let these flex with the content:

- Title weight/size may scale down a notch for very short titles (<4
  words) and up a notch for very long ones (>10 words), but stay within
  the serif family.
- Lists and quotes use the same color and accent palette as paragraphs;
  do not introduce new colors.
- When `images` is present, treat images as supportive — place one above
  the title or inline with the body, never as the dominant element.

## Title Treatment

Render `bundle.title` as the card's primary headline in serif. If any
entry in `bundle.accent_phrases` is a substring of the title, render that
phrase in italic within the headline (single accent preferred; if multiple
phrases match, italicize only the first).

## Body Treatment

For every entry in `bundle.accent_phrases` that appears in the body, wrap
the first occurrence in `<em>`. Respect any markdown emphasis already in
the source. Do not double-italicize.

## Meta Line

When `bundle.meta` is present, render a small monospace line near the top
or bottom of the card. Compose the line by joining non-empty meta values
with ` · ` and prefix it with a short label drawn from the usecase, e.g.:

- `<Usecase Title Case> · <value> · <value>`

**Date handling.** If `meta.date_today_display` is present, use it
verbatim as a meta segment (e.g. `April 17`). Otherwise, if
`meta.date_today` is present (format `YYYY-MM-DD`), reformat it to a
human-readable month-and-day form for display (e.g. `April 17`). Today's
date should be visible on every card whose bundle provides it. Place it
early in the meta line.

Omit missing segments. If `meta` is entirely absent, omit the line.

## Glosses

For each entry in `bundle.glosses` (e.g. `{"term": "小麻雀", "gloss":
"little sparrow"}`), wrap the first occurrence of `term` in the rendered
body so the gloss appears inline in italic, e.g.:
`小麻雀 *(little sparrow)*`. If the term does not appear in the body,
skip the gloss silently.

## Images

If `bundle.images` is present and small (each under ~200 KB decoded),
base64-inline them. Place at most one image above the title, or a single
inline image between body blocks. Larger images may be referenced by
relative path as a sibling of the output HTML. Always include `alt` text
when provided.

## Extras

`bundle.extras` is a freeform dict. You may honor these hints when set:

- `extras.tone`: `"quiet" | "warm" | "stark"` — nudge the accent color
  warmth and rule weight. Defaults to quiet.
- `extras.density`: `"airy" | "normal" | "compact"` — adjust padding and
  line-height. Defaults to normal.

Ignore any extras you do not recognize. Never let extras break the visual
identity invariants.

## Interactivity

- Title and body are `contenteditable` with a subtle hover and focus cue,
  so the user can make small edits before exporting.
- Three universal actions: **Download**, **Copy Image**, **Share**.
  - **Download** — PNG via bundled `html2canvas` at 3× pixel ratio.
  - **Copy Image** — clipboard write of the rendered PNG.
  - **Share** — `navigator.share` when available with the PNG blob; fall
    back to a small toast hint when not supported.
- A small toast element for feedback. No modals.
- `html2canvas` must be inlined into the HTML — no external `<script
  src>` at runtime.

### Action Placement and Styling

The actions should feel like part of the card and be clearly discoverable
as controls within a second or two of looking at the card.

- **Placement.** Inside the card's footer row, opposite the footer mark.
  Not below the card, outside the paper.
- **Form.** Inline SVG icons using universally recognized glyphs —
  Download (down-arrow-into-tray or cloud+down), Copy (overlapping
  rectangles), Share (Android three-node graph or iOS up-and-out arrow).
  No text labels, no emoji, no external icon fonts. Pick one Share glyph
  and be consistent.
- **Visibility.** The icons must be legible and clearly tappable. They
  are not plain-text affordances; they read as controls. Exact size,
  weight, spacing, background, hover/active treatment, and focus ring
  are design decisions — use judgment and keep them within the card's
  existing palette (ink, paper, one accent).
- **Accessibility.** Each button has a native `title=""` tooltip and a
  matching `aria-label` (`Download`, `Copy image`, `Share`). Interactive
  host is a `<button>` with a visible focus state.
- **On export.** Hide the actions during `html2canvas` capture (via a
  `data-noexport` attribute or a print-scoped rule). The exported PNG
  shows only the footer mark. Restore after capture.

The goal: a reader sees *the mark* and *three familiar, unmistakable
glyphs* as sibling meta at the card's foot. Present, legible, reachable
— still made of the same paper.

## Fonts

Prefer locally-available system serif and mono fonts (e.g.
`"Iowan Old Style", "Palatino", Georgia, serif` and `"SF Mono", "Menlo",
monospace`). Do not load web fonts from the network.

## Post-render

After writing the file, return its absolute path to the meta-skill. The
meta-skill is responsible for opening it in the browser.
