"""Skill Builder: generates SKILL.md and index.json."""

import json
import logging
import os
import sqlite3

from aicontext.records import IngestionResult
from aicontext.timestamps import get_timezone

logger = logging.getLogger(__name__)


def _approx(n):
    if not isinstance(n, (int, float)):
        try:
            n = int(n)
        except (ValueError, TypeError):
            return str(n)
    if n >= 1_000_000:
        return f"~{round(n / 1_000_000, 1)}M"
    if n >= 1_000:
        return f"~{round(n / 1000)}K"
    return str(n)


def _query_db(db_path, sql):
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


class SkillBuilder:
    def __init__(self, skill_root: str, db_path: str):
        self.skill_root = skill_root
        self.db_path = db_path
        self.ref_dir = os.path.join(skill_root, "reference")
        self.real_data_dir = os.path.dirname(db_path)

    def build(self, results: list[IngestionResult]) -> None:
        os.makedirs(self.ref_dir, exist_ok=True)
        os.makedirs(os.path.join(self.skill_root, "scripts"), exist_ok=True)

        self._generate_index()
        self._generate_reference_docs(results)
        self._generate_skill_md()
        logger.info("Skill output generated in %s", self.skill_root)

    def _generate_index(self) -> None:
        conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
        index = {}

        total = conn.execute('SELECT COUNT(*) FROM activity').fetchone()[0]
        index['total_records'] = total

        row = conn.execute(
            'SELECT MIN(SUBSTR(timestamp,1,10)), MAX(SUBSTR(timestamp,1,10)) FROM activity'
        ).fetchone()
        index['date_range'] = {'earliest': row[0], 'latest': row[1]}

        try:
            index['timezone'] = get_timezone()
        except Exception:
            index['timezone'] = 'unknown'

        sources = {}
        rows = conn.execute('''
            SELECT source, service, COUNT(*) as n,
                   MIN(SUBSTR(timestamp,1,10)) as earliest,
                   MAX(SUBSTR(timestamp,1,10)) as latest
            FROM activity GROUP BY source, service
            ORDER BY source, n DESC
        ''').fetchall()
        for source, service, count, earliest, latest in rows:
            if source not in sources:
                sources[source] = {'record_count': 0, 'services': {}}
            sources[source]['services'][service] = {'count': count, 'earliest': earliest, 'latest': latest}
            sources[source]['record_count'] += count
        index['sources'] = sources

        all_services = set()
        all_sources = set()
        for src, sdata in sources.items():
            all_sources.add(src)
            for svc in sdata['services']:
                all_services.add(svc)
        index['services_list'] = sorted(all_services)
        index['sources_list'] = sorted(all_sources)

        conn.close()

        index_path = os.path.join(self.skill_root, "index.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def _generate_reference_docs(self, results: list[IngestionResult]) -> None:
        for r in results:
            doc = r.source.get_reference_doc()
            if doc:
                doc = doc.replace("{DATA_DIR}", self.real_data_dir)
                path = os.path.join(self.ref_dir, f"{r.source.source_key}.md")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(doc)
        self._generate_activity_reference()

    def _generate_activity_reference(self) -> None:
        content = """\
# activity.db — Query Reference

## Schema

```sql
CREATE TABLE activity (
    id        INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,   -- local time with tz offset, e.g. 2026-04-09T03:41:00-07:00
    source    TEXT NOT NULL,
    service   TEXT NOT NULL,
    action    TEXT NOT NULL,
    title     TEXT NOT NULL,
    extra     TEXT,            -- JSON metadata (nullable)
    ref_type  TEXT,            -- 'local', 'table', or 'url'
    ref_id    TEXT
)
```

## Query Best Practices

**CRITICAL — Timestamp handling:** Timestamps are stored as ISO 8601 in LOCAL time
with timezone offset (e.g. `2026-04-02T23:14:00-07:00`). SQLite's `strftime()` and
`datetime()` silently convert these to UTC, shifting hours by the offset. This produces
WRONG results for any time-of-day or recency analysis. Use string operations instead:
- Extract hour: `SUBSTR(timestamp, 12, 2)` — NOT `strftime('%H', timestamp)`
- Extract date: `SUBSTR(timestamp, 1, 10)` — NOT `date(timestamp)`
- Day of week: `strftime('%w', SUBSTR(timestamp, 1, 10))` (date-only string has no offset — safe)
- Filter by recency: use `datetime('now', 'localtime', '-10 days')` — the `'localtime'` modifier is required to match stored local timestamps

**Merge multi-source queries with `IN`** instead of issuing separate queries per source:
```sql
SELECT timestamp, source, title
FROM activity
WHERE source IN ('claude_code', 'codex') AND action = 'prompted'
  AND timestamp > datetime('now', 'localtime', '-10 days')
ORDER BY timestamp DESC LIMIT 120
```

**Filter with `LIKE` before fetching** instead of dumping all rows:
```sql
SELECT timestamp, title FROM activity
WHERE source = 'chrome'
  AND (title LIKE '%job%' OR title LIKE '%resume%' OR title LIKE '%career%')
ORDER BY timestamp DESC LIMIT 50
```

**Use `extra` for richer signal.** The `extra` column is JSON:
- `claude_code` / `codex`: `project_path`, `git_branch`
- `chrome` (visited): `duration_sec`

```sql
-- Time spent per project
SELECT json_extract(extra, '$.project_path') AS project, COUNT(*) AS n
FROM activity WHERE source = 'claude_code' AND extra IS NOT NULL
GROUP BY project ORDER BY n DESC

-- Pages actually read (not just glanced at)
SELECT timestamp, title FROM activity
WHERE source = 'chrome'
  AND json_extract(extra, '$.duration_sec') > 60
ORDER BY timestamp DESC LIMIT 50
```
"""
        path = os.path.join(self.ref_dir, "activity.md")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _generate_skill_md(self) -> None:
        index_path = os.path.join(self.skill_root, "index.json")
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        total = index['total_records']
        dr = index['date_range']
        n_services = len(index['services_list'])
        tz = index.get('timezone', 'unknown')
        date_range_str = f"{dr['earliest']} to {dr['latest']}" if dr['earliest'] else "no data"

        svc_rows = []
        for source, sdata in index['sources'].items():
            for svc, info in sdata['services'].items():
                svc_rows.append((source, svc, info['count'], info['earliest'], info['latest']))
        svc_rows.sort(key=lambda r: r[2], reverse=True)

        top_svc_table = '| Source | Service | Records | Date Range |\n'
        top_svc_table += '|--------|---------|---------|------------|\n'
        for source, svc, count, earliest, latest in svc_rows[:15]:
            top_svc_table += f'| {source} | {svc} | {_approx(count)} | {earliest} to {latest} |\n'

        query_script = os.path.join(self.skill_root, "scripts", "query.py")

        skill_md = f"""---
name: personal-data
description: >
  Personal activity context — {_approx(total)} activities across {n_services} services ({date_range_str}).
  Use this skill to understand the user's recent work, browsing, and AI conversations.
---

# AI Context

## Tools

### scripts/query.py - SQL Query
Run from the same directory as this SKILL.md file:
```bash
# Simple queries — pass as argument:
python scripts/query.py "SELECT COUNT(*) FROM activity"

# Complex queries — pass via stdin (no quoting issues):
python scripts/query.py <<'EOF'
SELECT source, service, COUNT(*) as n
FROM activity
GROUP BY source, service
ORDER BY n DESC
EOF
```
Read-only SQL against {self.db_path}. Returns pipe-separated table. Max 200 rows.
Use `--max-cell 0` for full cell contents.

## What's Available

{_approx(total)} activity records across {n_services} services.

**Sources:**
{top_svc_table}
## Schema
`activity`: timestamp, source, service, action, title, extra (JSON), ref_type, ref_id

## Notes
- All timestamps in local time ({tz}) with timezone offset. SQLite's `strftime()`/`datetime()` silently convert to UTC — use `SUBSTR()` for hour/date extraction and `datetime('now', 'localtime', ...)` for recency filters. See `reference/activity.md` for details.
- `ref_type='local'`: ref_id is a path under `{self.real_data_dir}/reference_data/`, optionally with `#msg:<id>` suffix
- `ref_type='url'`: ref_id is the URL itself
- `reference/activity.md` — schema and SQL query best practices
- `reference/<source>.md` — source-specific field details and examples
"""

        path = os.path.join(self.skill_root, "SKILL.md")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(skill_md)
