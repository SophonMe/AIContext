---
name: canvas-usecase-today-in-history
description: >
  Curate a "today in my history" story from the user's personal activity
  database. Produces a content bundle with a single cohesive paragraph in
  the user's own voice. Never writes HTML — rendering is a separate skill.
---

# Today in My History

You are invoked by the `aicontext-canvas` meta-skill. Your job is to
research the user's personal activity history and produce a **content
bundle** matching `../../protocol.md`. You do not render anything. You do
not open a browser. You only write the bundle JSON.

Complete the entire task in one shot. Do not ask the user questions. Make
every judgment call yourself using the guidance below.

## Output

The meta-skill creates a per-run directory and passes it to you as
`<run-dir>`:

```
~/.aicontext/canvas/today-in-history/<YYYY-MM-DD-HHMM>/
```

Write the final bundle to `<run-dir>/.bundle.json`. Do not write anywhere
else.

## Data Access

- Default to `~/.aicontext/skill/scripts/query.py` for queries.
- If the helper doesn't expose what you need, read
  `~/.aicontext/data/activity.db` directly via `sqlite3` (read-only).
- You may use the agent's WebFetch and Chrome tools to pull supporting
  context from pages the user visited. Save any downloaded images under
  `<run-dir>/assets/<slug>/` and reference them from the bundle via
  relative `path`.

## Pick the Topic

Scan every year present in the data, earliest to latest, for activity on
the anchor day (the same month-day as today, in a past year). A single
entry on the anchor day is enough to anchor a story, as long as the
surrounding weeks, months, or years support a meaningful arc. **Narrative
quality matters, not activity count on the day itself.**

### What the reader wants

Remember what "today in my history" is. It is a small, private memory
ping — the reader wants to feel a flicker of recognition, meet a past
version of themselves for a moment, and close the card with a small
emotional charge. It is not a recap of a day. It is not a biography. It
is not an achievement log.

### Selection criteria

Evaluate at least three candidates against **all** of these. Reject any
candidate that fails a hard rule; pick the strongest among what remains.

1. **Would the reader recognize themselves in it?** Not "would they
   remember the day happened" — "would they see themselves *thinking,
   wanting, worrying*." If the candidate is just activity that happened
   near them, reject it.
2. **Does the thread have an interior?** A question being asked, a fear
   being poked at, an interest being formed, a decision being weighed,
   a skill being built, a relationship shifting. Just going somewhere,
   just watching something, just buying things — is not an interior.
   Reject candidates with no interior.
3. **Would the finished paragraph land with a small emotional charge?**
   Nostalgia, tenderness, rue, amusement at one's younger self,
   bittersweetness. If the best adjective for the likely finished
   paragraph is "informative," "productive," or "busy," the topic is
   wrong. Reject.
4. **Is it one story — not a day-in-the-life?** The chosen thread must
   be meaningfully stronger than every other thread on the day. If two
   or more threads on the anchor day are comparably strong, the day
   lacks a dominant story — pick a different year or reject the day.

If multiple candidates survive all four, prefer the one with the
strongest *interior* (criterion 2) — a clear question, decision, or
formation — over the one with the most activity. Prefer the one that
most rewards the reader meeting a past version of themselves.

### Common bad shapes (do not pick these)

- **The catalog.** A day reconstructed as a list of specific items the
  user consumed (songs, shows, videos, food). Specific but interior-less.
- **The enumeration.** The paragraph walks the logs in order ("you
  searched X, then Y, then Z, then W"). The reader doesn't care about
  query order, they care what the person was *after*. Group queries by
  intent and describe the intent; let one concrete query stand in for
  the rest.

## Research the Chosen Topic Deeply

Pull surrounding context across days, weeks, and months before and after
today's date. Fact-check every concrete claim against the logs before it
enters the paragraph. **Confidence must be HIGH or the claim is cut.**

Do not use exact clock times in prose. Write naturally ("that evening,"
"late that night") unless a specific moment is literally the story.

## Hold the Content Bar

Do not simply assemble what the research surfaces. A life has many parallel
threads on any given day — work, kids, errands, hobbies, news, etc. For
every sentence, ask: *is this on the same thread as the chosen topic, or is
it a co-occurring but unrelated thread?* If unrelated, cut it — even when
it is verified and vivid. Decoration is not structure. Specific ≠ relevant.

**Avoid:**

- Stacked setup facts at the opening
- Framings like "A year ago today you were doing X when Y pulled you in."
  Do not use adjacent-but-unrelated activity (the work task you were on,
  the errand you were running, the show you were watching) as a runway
  into the real story. That is a stacked setup, not an opening.
- Trailing off-thread activity at the close. Do not end with "late that
  night, unrelated…" or "meanwhile, you also…" style tails. If you catch
  yourself having to hedge with *unrelated*, *unexplained*, *somehow*,
  *sideways*, or *randomly*, that sentence is off-thread — cut it.
- Mid-paragraph digressions narrated in the first person ("somebody
  searched 'fries' in image search — very much a small-kid-in-the-back-
  seat kind of search"). Even when charming, these derail the thread.
- Symbol-hunting (reading grocery orders or TV shows as metaphors for the
  main event)
- Literary flourishes that were not earned by the data
- Summarizing theses at the close

**Prefer:**

- An opening that names what the person was **doing** — the interior
  act: weighing a choice, chasing a fear, dressing a wish, pricing out a
  possibility. A specific action from inside the thread follows as
  evidence of that act, never as the opening itself. If your first
  sentence reads like screen narration ("you opened X and searched Y"),
  stop and name the act first.
- The user's verbatim words where available (quote them)
- A concrete closing image **from inside the chosen thread** — an object,
  an action, a search, a message that belongs to the arc. Not a thesis,
  and not an unrelated later event in the same day.
- Natural time markers, not timestamps

## The Thread Discipline Test

The **anchor day** is the historical day-of-year in a past year — the
same month-day as today's date, but in the year you chose (e.g. today
is April 18 and the story is from April 18, 2021). The thread can extend
in either direction around the anchor day — earlier context that set up
the story, later beats that resolved it.

Before you write, name the **entry point**, the **middle beats**, and the
**closing beat** of the chosen thread:

- The entry point is the log entry on the anchor day that first
  unambiguously places the story on that day. This is what gives the
  piece its "today in history" standing.
- The middle beats are log entries that are part of the same thread but
  may fall on days, weeks, months, or even years surrounding the anchor
  day — earlier context, later developments, recurring touches. Use them
  to build the arc.
- The closing beat is the last log entry that is unambiguously part of
  this story. It does **not** have to fall on the anchor day — threads
  often resolve days, weeks, or months later, and the close should land
  wherever the arc actually closes in the data.

Use natural time markers when you move off the anchor day ("a few weeks
earlier," "that summer," "by the end of the year"), not calendar dates.

The opening sentence must use the entry point (or a direct paraphrase of
it). The closing sentence must use the closing beat (or a direct paraphrase
of it). Every sentence in between must be part of the same thread, even
if it comes from a different day, week, month, or year.

After drafting, do a thread pass: for every sentence, ask *"is this on
the chosen thread?"* — not *"is this on the anchor day?"*. A sentence
can be on-thread and off-day; that is fine. A sentence is off-thread if
you can only keep it by explaining *why* it's there (*"unrelated"*,
*"sideways"*, *"randomly"*, *"meanwhile"*) — cut those. The reader should
never feel the writer apologizing for a detour.

## Write the Paragraph

One short, cohesive paragraph. Second person ("you"). No headers, no
bullets, no timestamps. **Write in English only.** If the source logs
contain non-English text (e.g., Chinese search queries or prompts),
translate or paraphrase into English prose; do not preserve the original
script inline. Do not populate the `glosses` field.

The language the user typed in is usually incidental — render the
*content* of a query or prompt rather than noting which language it was
in, unless the language itself is part of the thread.

**Do not use hyphens (`-`) or em/en dashes (`—`, `–`) in the body.** Use
commas, periods, or parentheses instead. Rewrite compound constructions
naturally.

## Produce the Bundle

Fill in the bundle fields:

- `usecase`: `"today-in-history"`
- `slug`: a short, filesystem-safe id derived from the topic and year,
  e.g. `"2019-sf-arrival"`. Lowercase, hyphens only.
- `title`: a short headline for the card (not the full paragraph — think
  3–8 words with optional italic accent phrase isolated in
  `accent_phrases`).
- `body`: the paragraph.
- `meta`:
  - `date_today`: today's date in `YYYY-MM-DD`. **Required** — the
    renderer uses this to label the card.
  - `date_today_display`: today's date in human-readable form, e.g.
    `"April 17"` (month name + day, no year). The renderer prefers this
    over `date_today` when present.
  - `location`: city/region where the original event happened, if
    inferable from the data. Omit otherwise.
  - `year`: the year the original event happened.
- `accent_phrases`: zero or more phrases from `title` or `body` the
  renderer may italicize. Keep the list short (0–2).
- `glosses`: leave empty — this usecase writes English only.
- `hints.preferred_variant`: leave `null` — the agent picks the renderer.

## Working Style

- Parallelize research where independent; sequence where dependent.
- Keep your own process notes out of the bundle — nothing ends up in
  `body` that wasn't earned by the data.
- When in doubt between two framings, pick the quieter one.
- When in doubt about the chosen topic's resolution, drop it and pick
  another candidate.
