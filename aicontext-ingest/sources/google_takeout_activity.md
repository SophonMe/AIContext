# Google Takeout — My Activity

## Overview

Google Takeout's "My Activity" export contains a user's activity history across
Google services: Search, YouTube, Maps, Chrome, Gmail, Translate, Gemini, etc.

- **source_key**: `"google_takeout_activity"`
- **source**: `"google"`
- **service**: varies by Google product (see below)
- **mode**: `static`

## Data Location

The export is typically a directory called `Takeout/` or `My Activity/` inside
a larger Takeout archive. Within it, each Google service has its own
subdirectory containing a `MyActivity.html` (or sometimes `My Activity.html`)
file. The directory structure looks like:

```
Takeout/My Activity/
├── Search/MyActivity.html
├── YouTube/MyActivity.html
├── Maps/MyActivity.html
├── Chrome/MyActivity.html
├── Gmail/MyActivity.html
├── Google Translate/MyActivity.html
├── Gemini Apps/MyActivity.html
└── ...
```

The user's path may point to `Takeout/`, `Takeout/My Activity/`, or directly
to the directory containing the service subdirectories. Scan for subdirectories
that contain an HTML file named `MyActivity.html` or similar variations.

## Data Format

Each `MyActivity.html` file is an HTML document with activity entries. The
format uses nested `<div>` elements. Each activity entry typically contains:

- A **timestamp** (human-readable format)
- An **action description** (e.g., "Searched for", "Visited", "Watched")
- A **title or content** (the search query, page title, video title, etc.)
- Optional **links** (URLs to the content)

### Timestamp Format

Timestamps appear as human-readable strings. Common formats:

- `"Mar 10, 2026, 10:25:03 PM PDT"`
- `"6 Apr 2026, 19:29:39 GMT-07:00"`

Note: there may be Unicode non-breaking spaces (`\u202f`, `\xa0`) between
the time and AM/PM. Normalize these to regular spaces before parsing.

The timezone abbreviation (PDT, EST, CST, etc.) needs to be mapped to a UTC
offset for conversion. Common mappings:
- PDT=-7, PST=-8, EDT=-4, EST=-5, CDT=-5, CST=-6, MDT=-6, MST=-7, UTC=0, GMT=0

## Service Mapping

Map the subdirectory name to a service key. Common directories and their
service values:

| Directory Name | service | Typical actions |
|---------------|---------|-----------------|
| Search | `search` | `searched` |
| YouTube | `youtube` | `watched` |
| Maps | `maps` | `visited`, `explored` |
| Chrome | `chrome` | `visited` |
| Gmail | `gmail` | `used` |
| Google Translate | `translate` | `translated` |
| Gemini Apps | `gemini` | `prompted`, `received` |
| AI Mode | `ai_mode` | `searched` |
| Image Search | `image_search` | `searched` |
| Google Flights | `flights` | `searched` |
| Google Shopping | `shopping` | `searched`, `visited` |
| News | `news` | `visited` |
| Google Play Store | `play_store` | `visited` |
| Discover | `discover` | `visited` |
| Google Books | `books` | `visited` |
| Google Drive | `drive` | `used` |

## Action Extraction

Each entry's text starts with an action prefix followed by the content.
**Important:** Google uses non-breaking spaces (`\xa0`) between the action
word and the content — normalize these to regular spaces before matching.

Parse the action from the prefix. Known prefixes and their action values:

- "Searched for ..." → `searched`
- "Searched ..." → `searched`
- "Visited ..." → `visited`
- "Watched ..." → `watched`
- "Translated ..." → `translated`
- "Viewed ..." → `visited`
- "Listened to ..." → `listened`
- "Directions to ..." → `navigated`
- "Explored ..." → `explored`
- "Opened ..." → `visited`
- "Called ..." → `called`
- "Saved ..." → `saved`
- "Liked ..." → `liked`
- "Disliked ..." → `disliked`
- "Subscribed to ..." → `subscribed`
- "Shared ..." → `shared`
- "Dismissed ..." → `dismissed`
- "Prompted ..." → `prompted`
- "Created ..." → `created`
- "Defined ..." → `searched`
- "Read ..." → `read`
- "Tracked ..." → `tracked`
- "Used ..." → `used`

Entries without a recognized action prefix but with a link (e.g. Maps place
lookups that are just `"<a>Place Name</a>"`) should be treated as `visited`.

**Skip entries that have no recognized action prefix and no link.** Do not
use a fallback action — if the action cannot be determined, drop the record.

## Extra Fields

Service-specific metadata can be extracted when available:

- **youtube**: `channel` (the channel name, if present)
- **maps**: `address` (location text), `lat`/`lon` (coordinates from URLs)
- **translate**: `lang_from`, `lang_to`, `query`

## Gemini Responses

Gemini Apps entries include the assistant's reply. Within a content cell,
the layout is:

```
Prompted <query>
<a>Audio included.</a>           (optional, when voice input was used)
<timestamp>
<p>response text</p>
```

For each Gemini entry, emit TWO records sharing the same timestamp:
1. action=`prompted` with the user's query as the title.
2. action=`received` with the response text (from the `<p>` block) as the
   title. Skip this second record if the response text is empty or missing.

AI Mode entries do NOT contain response text — only the search query and,
sometimes, follow-up queries from the same thread. Emit a single `searched`
record per AI Mode entry.

## Edge Cases

- Some entries may lack timestamps — skip those records
- Entries may contain only a timestamp with no meaningful content — skip
- Service directories may have names in the user's locale language
- The export may include services not listed above — skip unknown services
