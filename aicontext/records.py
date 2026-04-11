"""Data structures for aicontext."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActivityRecord:
    timestamp: str          # ISO 8601 with offset, no fractional seconds
    source: str
    service: str
    action: str
    title: str              # REQUIRED, never empty
    extra: dict | None = None
    ref_type: str | None = None   # "local" | "url" | None
    ref_id: str | None = None


@dataclass
class ReferenceFile:
    path: str               # relative to data/reference_data/
    data: dict | list       # JSON-serializable


@dataclass
class IngestionResult:
    source: Any             # DataSource instance
    records_parsed: int = 0
    records_rejected: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    reference_files_written: int = 0
    reference_files_overwritten: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
