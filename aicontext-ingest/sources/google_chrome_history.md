# Google Chrome History (Takeout JSON)

## Overview

Chrome browsing history exported via Google Takeout as a JSON file.
This is NOT the live Chrome SQLite database (that's handled by a built-in
source). This is the static Takeout export.

- **source**: `"google"`
- **service**: `"chrome"`
- **action**: `"visited"`
- **mode**: `static`

## Data Location

Typically at `Takeout/Chrome/BrowserHistory.json` or similar path. The file
may also be named `History.json` or `Browser History.json`. Look for a JSON
file containing a `"Browser History"` key.

## Data Format

```json
{
  "Browser History": [
    {
      "title": "Example Page",
      "url": "https://example.com/page",
      "time_usec": 13350000000000000,
      "page_transition": "link"
    }
  ]
}
```

### Timestamp Format

The `time_usec` field may be:
- **Unix microseconds** (since 1970): values around 1.7×10¹⁵
- **Chrome/WebKit microseconds** (since 1601-01-01): values around 1.3×10¹⁶

Distinguish by magnitude: Chrome epoch values are roughly 10× larger than
Unix epoch values. For Chrome epoch: `unix_sec = (time_usec / 1_000_000) - 11644473600`.

## What To Extract

- **title**: `title` field (use "Untitled" if empty/missing)
- **timestamp**: from `time_usec`
- **ref_type**: `"url"`
- **ref_id**: the `url` field
- **extra.page_transition**: the `page_transition` field (if present)

## Edge Cases

- Entries without `time_usec` — skip
- The `title` field may be empty or missing — use "Untitled"
- The root JSON key may vary (check for `"Browser History"` or iterate
  top-level keys looking for an array)
- Extremely old timestamps may appear from imported bookmarks — filter
  to reasonable date ranges if needed
