"""Ingester: orchestrates source ingestion, dedup, and database writes."""

from __future__ import annotations

import json
import logging
import os
import time
from collections import Counter
from dataclasses import dataclass

from aicontext.records import ActivityRecord, ReferenceFile, IngestionResult
from aicontext.sources.base import DataSource
from aicontext.timestamps import validate_iso_timestamp
from aicontext.database import create_database, insert_records, update_record, load_all_records
from aicontext.dedup import (
    collapse_consecutive, compute_default_dedup_key, content_hash_json,
    normalize_for_dedup, pick_older_record, records_equal,
)

logger = logging.getLogger(__name__)


@dataclass
class _PendingRecord:
    record: ActivityRecord
    source: DataSource
    result: IngestionResult


class Ingester:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "activity.db")
        self.ref_dir = os.path.join(data_dir, "reference_data")

    def _resolve_local_ref_path(self, ref_id: str) -> str | None:
        if not ref_id:
            return None
        rel_path = ref_id.split("#", 1)[0]
        if os.path.isabs(rel_path):
            return None
        resolved = os.path.realpath(os.path.join(self.ref_dir, rel_path))
        ref_root = os.path.realpath(self.ref_dir)
        try:
            if os.path.commonpath([ref_root, resolved]) != ref_root:
                return None
        except ValueError:
            return None
        return resolved

    def _ensure_db(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.ref_dir, exist_ok=True)
        if not os.path.exists(self.db_path):
            create_database(self.db_path)

    def _validate_record(self, rec: ActivityRecord) -> str | None:
        if not validate_iso_timestamp(rec.timestamp):
            return f"bad timestamp: {rec.timestamp!r}"
        if not rec.title or not rec.title.strip():
            return "empty title"
        if not rec.source or not rec.source.strip():
            return "empty source"
        if not rec.service or not rec.service.strip():
            return "empty service"
        if not rec.action or not rec.action.strip():
            return "empty action"
        if (rec.ref_type is None) != (rec.ref_id is None):
            return f"ref_type/ref_id mismatch: type={rec.ref_type!r} id={rec.ref_id!r}"
        if rec.ref_type is not None and rec.ref_type not in ("local", "url"):
            return f"invalid ref_type: {rec.ref_type!r}"
        if rec.ref_type == "local":
            ref_path = self._resolve_local_ref_path(rec.ref_id)
            if ref_path is None:
                return f"invalid local ref path: {rec.ref_id!r}"
            if not os.path.exists(ref_path):
                return f"local ref file not found: {rec.ref_id.split('#', 1)[0]}"
        if rec.extra is not None:
            if not isinstance(rec.extra, dict):
                return f"extra is not a dict: {type(rec.extra).__name__}"
            try:
                json.dumps(rec.extra)
            except (TypeError, ValueError) as e:
                return f"extra not JSON-serializable: {e}"
        return None

    def _load_ref_meta(self) -> dict:
        meta_path = os.path.join(self.ref_dir, "_meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_ref_meta(self, meta: dict) -> None:
        meta_path = os.path.join(self.ref_dir, "_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    def _ingest_references(self, source: DataSource, source_path: str,
                           source_config: dict) -> tuple[int, int, int]:
        ref_files = source.ingest_reference(source_path, source_config, db_path=self.db_path)
        if not ref_files:
            return 0, 0, 0

        meta = self._load_ref_meta()
        meta_changed = False
        written = 0
        overwritten = 0
        skipped = 0

        for ref_file in ref_files:
            out_path = self._resolve_local_ref_path(ref_file.path)
            if out_path is None:
                raise ValueError(f"invalid reference path from source {source.source_key}: {ref_file.path!r}")

            data = ref_file.data
            if os.path.exists(out_path):
                try:
                    with open(out_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    data = source.merge_reference(existing_data, data)
                except Exception:
                    pass

            new_hash = content_hash_json(data)
            serialized = json.dumps(data, ensure_ascii=False)
            new_size = len(serialized.encode("utf-8"))
            stored = meta.get(ref_file.path)
            if isinstance(stored, dict) and stored.get("content_hash") == new_hash:
                skipped += 1
                continue

            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            if os.path.exists(out_path):
                overwritten += 1
            else:
                written += 1

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(serialized)

            meta[ref_file.path] = {"content_hash": new_hash, "size": new_size}
            meta_changed = True

        if meta_changed:
            self._save_ref_meta(meta)

        return written, overwritten, skipped

    def _dedup_records(self, pending_records: list[_PendingRecord]
                       ) -> tuple[list[ActivityRecord], list[tuple[int, ActivityRecord]], int, int, int]:
        batch_map: dict[str, _PendingRecord] = {}
        batch_dupes = 0

        for pending in pending_records:
            key = pending.source.dedup_key(pending.record)
            existing_pending = batch_map.get(key)
            if existing_pending is None:
                batch_map[key] = pending
                continue

            batch_dupes += 1
            winner = pick_older_record(existing_pending.record, pending.record)
            loser = pending if winner is existing_pending.record else existing_pending
            loser.result.records_skipped += 1

            if winner is pending.record:
                batch_map[key] = pending

        existing_rows = load_all_records(self.db_path)
        existing_map: dict[str, tuple[int, ActivityRecord]] = {}
        for row_id, rec in existing_rows:
            key = compute_default_dedup_key(rec.title, rec.service, rec.action, rec.timestamp)
            current = existing_map.get(key)
            if current is None:
                existing_map[key] = (row_id, rec)
                continue
            if pick_older_record(rec, current[1]) is rec:
                existing_map[key] = (row_id, rec)

        to_insert = []
        to_update = []
        skipped = 0

        for key, pending in batch_map.items():
            new_rec = pending.record
            if key not in existing_map:
                to_insert.append(new_rec)
                pending.result.records_inserted += 1
                continue

            ex_id, ex_rec = existing_map[key]
            winner = pick_older_record(ex_rec, new_rec)
            if winner is new_rec and not records_equal(ex_rec, new_rec):
                to_update.append((ex_id, new_rec))
                pending.result.records_updated += 1
            else:
                skipped += 1
                pending.result.records_skipped += 1

        return to_insert, to_update, skipped, batch_dupes

    def build(self, sources: list[tuple[DataSource, str]]) -> list[IngestionResult]:
        """Ingest a list of (DataSource, source_path) pairs.

        Returns list of IngestionResult, one per source.
        """
        self._ensure_db()

        results = []
        pending_records: list[_PendingRecord] = []

        for source, source_path in sources:
            t0 = time.time()
            result = IngestionResult(source=source)
            logger.info("=== %s ===", source.name)

            try:
                written, overwritten, ref_skipped = self._ingest_references(source, source_path, {})
                result.reference_files_written = written + overwritten
                result.reference_files_overwritten = overwritten
                if written or overwritten or ref_skipped:
                    logger.debug("  references: %d written, %d overwritten, %d unchanged",
                                 written, overwritten, ref_skipped)

                raw_records = source.ingest_activity(source_path, {})
                result.records_parsed = len(raw_records)
                logger.debug("  parsed %d activity records", len(raw_records))

                valid_records = []
                reject_reasons = Counter()
                for rec in raw_records:
                    err = self._validate_record(rec)
                    if err:
                        reject_reasons[err.split(":")[0]] += 1
                        result.records_rejected += 1
                    else:
                        valid_records.append(rec)

                if result.records_rejected:
                    logger.debug("  rejected %d: %s", result.records_rejected, dict(reject_reasons))

                if not valid_records:
                    result.elapsed_seconds = time.time() - t0
                    results.append(result)
                    continue

                valid_records = collapse_consecutive(
                    valid_records,
                    key_fn=lambda rec: (rec.service, rec.action, normalize_for_dedup(rec.title)),
                )
                logger.debug("  after collapse: %d records", len(valid_records))

                for rec in valid_records:
                    pending_records.append(_PendingRecord(record=rec, source=source, result=result))

            except Exception as exc:
                logger.warning("  %s error: %s", source.name, exc)
                logger.debug("  traceback:", exc_info=True)
                result.errors.append(str(exc))

            result.elapsed_seconds = time.time() - t0
            results.append(result)

        if pending_records:
            to_insert, to_update, skipped, batch_dupes = self._dedup_records(pending_records)
            logger.debug("dedup: %d new, %d updates, %d skipped, %d batch-dupes",
                         len(to_insert), len(to_update), skipped, batch_dupes)

            if to_insert:
                insert_records(self.db_path, to_insert)
            for row_id, rec in to_update:
                update_record(self.db_path, row_id, rec)

        for r in results:
            if r.errors:
                logger.info("%s: error — %s", r.source.name, r.errors[0])
            else:
                logger.info("%s: parsed=%d new=%d updated=%d skipped=%d rejected=%d (%.1fs)",
                            r.source.name, r.records_parsed, r.records_inserted,
                            r.records_updated, r.records_skipped, r.records_rejected,
                            r.elapsed_seconds)

        return results
