"""Microsoft Edge local browser data source."""

import logging
import os
import shutil
import sqlite3
import tempfile

from aicontext.sources.base import DataSource
from aicontext.records import ActivityRecord
from aicontext.timestamps import parse_chrome_epoch

logger = logging.getLogger(__name__)


def _copy_and_query(db_path, queries):
    if not os.path.exists(db_path):
        return [[] for _ in queries]
    tmp_path = None
    conn = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(tmp_fd)
        shutil.copy2(db_path, tmp_path)
        conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        results = []
        for query in queries:
            try:
                results.append(conn.execute(query).fetchall())
            except sqlite3.Error:
                results.append([])
        return results
    except (PermissionError, sqlite3.DatabaseError):
        return [[] for _ in queries]
    finally:
        if conn:
            conn.close()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


class BrowserEdgeSource(DataSource):

    @property
    def name(self) -> str:
        return "Edge Browser"

    @property
    def source_key(self) -> str:
        return "browser_edge"

    def ingest_activity(self, source_path: str, source_config: dict) -> list[ActivityRecord]:
        visits_query = """
            SELECT v.visit_time, v.visit_duration, u.url, u.title,
                   ca.total_foreground_duration
            FROM visits v
            JOIN urls u ON v.url = u.id
            LEFT JOIN context_annotations ca ON ca.visit_id = v.id
        """
        downloads_query = """
            SELECT d.start_time, d.target_path, d.tab_url, d.total_bytes, d.mime_type
            FROM downloads d
        """
        visit_rows, download_rows = _copy_and_query(source_path, [visits_query, downloads_query])

        records = []
        for row in visit_rows:
            title = row["title"]
            if not title:
                continue
            try:
                ts = parse_chrome_epoch(row["visit_time"])
            except Exception:
                continue

            extra = {}
            duration = row["visit_duration"]
            if duration and duration > 0:
                extra["duration_sec"] = round(duration / 1_000_000, 1)
            foreground = row["total_foreground_duration"]
            if foreground and foreground > 0:
                extra["foreground_sec"] = round(foreground / 1_000_000, 1)

            records.append(ActivityRecord(
                timestamp=ts, source="edge", service="edge", action="visited",
                title=title, extra=extra or None,
                ref_type="url", ref_id=row["url"],
            ))

        for row in download_rows:
            target_path = row["target_path"]
            if not target_path:
                continue
            try:
                ts = parse_chrome_epoch(row["start_time"])
            except Exception:
                continue

            filename = os.path.basename(target_path)
            extra = {}
            if row["total_bytes"] and row["total_bytes"] > 0:
                extra["size_bytes"] = row["total_bytes"]
            if row["mime_type"] and row["mime_type"].strip():
                extra["mime_type"] = row["mime_type"]

            records.append(ActivityRecord(
                timestamp=ts, source="edge", service="edge", action="downloaded",
                title=filename, extra=extra or None,
                ref_type="url" if row["tab_url"] else None,
                ref_id=row["tab_url"] or None,
            ))

        return records

    def get_reference_doc(self) -> str:
        return """# Edge Browser Reference

Local Microsoft Edge browser history (visits and downloads).

## Services
| Service | Description |
|---------|-------------|
| edge | Local Edge browser history |

## Actions
| Action | Meaning |
|--------|---------|
| visited | Page visit |
| downloaded | File download |

## Extra Fields
| Field | Type | Description |
|-------|------|-------------|
| duration_sec | number | Total visit duration in seconds |
| foreground_sec | number | Time spent in foreground in seconds |
| size_bytes | integer | Download file size |
| mime_type | string | Download MIME type |

## Query Examples
```sql
SELECT timestamp, title, json_extract(extra, '$.duration_sec') as duration
FROM activity WHERE source='edge' AND action='visited'
ORDER BY timestamp DESC LIMIT 20;
```
"""
