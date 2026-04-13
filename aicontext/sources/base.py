"""Abstract base class for data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, final

from aicontext.records import ActivityRecord, ReferenceFile
from aicontext.dedup import compute_default_dedup_key


class DataSource(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'Claude Code'."""
        ...

    @property
    @abstractmethod
    def source_key(self) -> str:
        """Machine key, e.g. 'claude_code'."""
        ...

    @abstractmethod
    def ingest_activity(self, source_path: str, source_config: dict) -> list[ActivityRecord]:
        ...

    def ingest_reference(self, source_path: str, source_config: dict,
                         db_path: str | None = None) -> list[ReferenceFile] | None:
        return None

    @final
    def dedup_key(self, record: ActivityRecord) -> str:
        return compute_default_dedup_key(
            record.title, record.service, record.action, record.timestamp,
        )

    @final
    def resolve_batch_conflict(self, a: ActivityRecord, b: ActivityRecord) -> ActivityRecord:
        return a if a.timestamp <= b.timestamp else b

    @final
    def resolve_conflict(self, existing: ActivityRecord, new: ActivityRecord) -> ActivityRecord:
        return existing if existing.timestamp <= new.timestamp else new

    @final
    def merge_reference(self, existing_data: Any, new_data: Any) -> Any:
        return new_data

    @property
    def mode(self) -> str:
        """'dynamic' (default) or 'static'.

        Static sources are skipped by the hourly sync daemon.
        User-triggered sync runs all sources regardless of mode.
        """
        return "dynamic"

    @abstractmethod
    def get_reference_doc(self) -> str:
        ...
