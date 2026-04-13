# DataSource Protocol

This document defines the interface contract, field conventions, and coding
rules for implementing a data source for AIContext.

## DataSource Abstract Base Class

Every data source must subclass `DataSource` and implement the required methods.
The class lives in `aicontext/sources/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Any, final
from aicontext.records import ActivityRecord, ReferenceFile
from aicontext.dedup import compute_default_dedup_key


class DataSource(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'Amazon Orders'."""
        ...

    @property
    @abstractmethod
    def source_key(self) -> str:
        """Machine key, e.g. 'amazon_orders'. Must be a valid Python identifier."""
        ...

    @abstractmethod
    def ingest_activity(self, source_path: str, source_config: dict) -> list[ActivityRecord]:
        """Parse raw data and return activity records.

        source_path: file or directory path (from config.json).
        source_config: currently unused (empty dict), reserved for future settings.
        """
        ...

    def ingest_reference(self, source_path: str, source_config: dict,
                         db_path: str | None = None) -> list[ReferenceFile] | None:
        """Optional: return full-content reference files (JSON).
        Default: None (no reference data)."""
        return None

    @property
    def mode(self) -> str:
        """'dynamic' (default) or 'static'.
        Static sources are skipped by the hourly sync daemon.
        User-triggered sync runs all sources regardless of mode."""
        return "dynamic"

    @abstractmethod
    def get_reference_doc(self) -> str:
        """Return Markdown documentation for this source.
        Used to generate reference/<source_key>.md in the skill output."""
        ...

    # The following methods are @final — do not override:
    # dedup_key(record) — MD5 hash for deduplication
    # resolve_batch_conflict(a, b) — older timestamp wins
    # resolve_conflict(existing, new) — older timestamp wins
    # merge_reference(existing_data, new_data) — new data replaces old
```

## ActivityRecord

```python
from dataclasses import dataclass

@dataclass
class ActivityRecord:
    timestamp: str          # ISO 8601 with timezone offset, no fractional seconds
    source: str             # Vendor/platform (e.g., "amazon", "google")
    service: str            # Product/feature (e.g., "orders", "search")
    action: str             # Past-tense verb (e.g., "purchased", "searched")
    title: str              # REQUIRED, never empty — primary content
    extra: dict | None = None       # JSON-serializable metadata, or None
    ref_type: str | None = None     # "local" | "url" | None
    ref_id: str | None = None       # Path or URL — must be set iff ref_type is set
```

## ReferenceFile

```python
@dataclass
class ReferenceFile:
    path: str               # Relative to ~/.aicontext/data/reference_data/
    data: dict | list       # JSON-serializable content
```

## Timestamp Helpers

Available from `aicontext.timestamps`:

- `parse_iso_utc(iso_str)` — Parse ISO 8601 string (handles Z, offsets, fractional
  seconds). Returns local ISO with timezone offset.
- `to_local_iso(dt_utc)` — Convert a `datetime` to local ISO with timezone offset.
  If the datetime is naive, it's assumed UTC.
- `validate_iso_timestamp(ts)` — Returns True if the string matches
  `YYYY-MM-DDTHH:MM:SS+HH:MM` format.
- `parse_chrome_epoch(chrome_usec)` — Chrome microseconds since Windows epoch.
- `parse_mac_absolute(mac_sec)` — macOS absolute time (seconds since 2001-01-01).

All timestamps are stored as `YYYY-MM-DDTHH:MM:SS+HH:MM` in local time.

## Field Conventions

These conventions are consistent with existing built-in sources. Follow them
so queries across sources produce coherent results.

| Field | Convention | Examples |
|-------|-----------|----------|
| `source` | Vendor/platform, lowercase | `"amazon"`, `"google"`, `"openai"`, `"anthropic"` |
| `service` | Product/feature within the vendor | `"orders"`, `"search"`, `"calendar"`, `"chatgpt"`, `"prime_video"` |
| `action` | Past-tense verb describing user action | `"purchased"`, `"searched"`, `"visited"`, `"watched"`, `"prompted"`, `"received"`, `"downloaded"`, `"attended"`, `"listened"` |
| `title` | Primary human-readable content | Product name, search query, page title, message text |
| `extra` | Structured metadata as JSON dict | `{"price": 12.99, "currency": "USD"}`, `{"duration_sec": 120}` |

### Existing source/service/action combinations

Avoid conflicts with these already-registered combinations:

| source | service | actions |
|--------|---------|---------|
| `claude_code` | `claude_code` | `prompted`, `received` |
| `codex` | `codex` | `prompted`, `received` |
| `chrome` | `chrome` | `visited`, `downloaded` |
| `edge` | `edge` | `visited`, `downloaded` |
| `safari` | `safari` | `visited` |
| `dia` | `dia` | `visited`, `downloaded` |

## Data Consistency

AIContext handles data consistency automatically. Understanding these guarantees
helps you write correct `ingest_activity()` implementations.

### Activity records

- **Deduplication**: Records are deduped by MD5 hash of
  `(service + action + normalized_title + rounded_timestamp)`. Your code does
  not need to handle dedup — return all records and the ingester deduplicates.
- **Consecutive collapse**: Identical consecutive records (same service + action
  + title) are collapsed automatically.
- **Validation**: The ingester validates every record — bad timestamps, empty
  titles, ref_type/ref_id mismatches are rejected with warnings. Individual bad
  records do not crash ingestion.
- **Conflict resolution**: When the same record appears in multiple syncs, the
  older timestamp wins. Records are never deleted, only inserted or updated.
- **Idempotent sync**: `ingest_activity()` should return ALL records every time
  (not track "what's new"). The ingester handles incremental updates.

### Reference data

- **Merge then hash**: When a reference file already exists on disk, the
  ingester loads it and calls `merge_reference(existing_data, new_data)`.
  The default implementation replaces old data with new entirely (no
  field-level merging). After merging, a SHA-256 content hash is computed.
  If the hash matches the stored hash in `_meta.json`, the write is skipped.
  If different, the file is written to disk and the hash is updated.
- **Storage**: Reference files are stored as JSON under
  `~/.aicontext/data/reference_data/<source_key>/`.

### ref_type / ref_id patterns

Activity records can optionally link to reference data:

- `ref_type="local"`, `ref_id="<source_key>/<file>.json"` — links to a file
  under `reference_data/`. Use `#fragment` suffix for sub-record linking
  (e.g., `"claude_code/session.json#msg:123"`).
- `ref_type="url"`, `ref_id="https://..."` — links to an external URL.
- Both `ref_type` and `ref_id` must be set together, or both `None`.

## Coding Rules

- **Defensive parsing**: Skip bad individual records with `logger.warning()`.
  Never raise exceptions for individual malformed rows/entries — log and continue.
- **Encoding**: Handle `utf-8-sig` for CSV files (common in Windows exports).
  Try `utf-8` first, fall back if needed.
- **Mode**: Return `"static"` from the `mode` property for one-time data exports.
  Return `"dynamic"` for data that updates continuously.
- **source_path**: Can be a file or a directory depending on the data source.
  Handle whichever is appropriate.
- **Write location**: Write your implementation to
  `~/.aicontext/data_sources/<source_key>.py`
- **Never modify** files under `aicontext/`.
- **Imports**: You can import from `aicontext.sources.base`, `aicontext.records`,
  and `aicontext.timestamps`. Standard library modules (`csv`, `json`, `os`,
  `logging`, `re`, `glob`, `sqlite3`, `html`, etc.) are all available.
