#!/usr/bin/env python3
"""Read-only SQL query tool for aicontext data.

Usage:
    python query.py "SELECT COUNT(*) FROM activity"
    python query.py "SELECT ..." --max-cell 0
"""
import sqlite3
import sys
import os
import argparse
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')
DEFAULT_DB = 'activity.db'
MAX_ROWS = 200
DEFAULT_MAX_CELL = 120
FOLD_MIN_ROWS = 10

WRITE_KEYWORDS = {'insert', 'update', 'delete', 'drop', 'alter', 'create', 'attach', 'detach'}


def escape_cell(val):
    s = str(val) if val is not None else ''
    s = s.replace('\\', '\\\\')
    s = s.replace('|', '\\|')
    s = s.replace('\n', '\\n').replace('\r', '')
    return s


def truncate_cell(s, max_cell):
    if max_cell > 0 and len(s) > max_cell:
        return s[:max_cell - 3] + '...'
    return s


def compress_timestamps(headers, rows):
    if 'timestamp' not in headers:
        return None, headers, rows

    ts_idx = headers.index('timestamp')
    ts_values = [row[ts_idx] for row in rows]
    if not ts_values:
        return None, headers, rows

    parsed = [str(ts) if ts is not None else '' for ts in ts_values]

    ts_pattern = re.compile(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})?$')
    matches = [ts_pattern.match(p) for p in parsed]
    if not all(matches):
        return None, headers, rows

    dates = [m.group(1) + '-' + m.group(2) + '-' + m.group(3) for m in matches]
    years = [m.group(1) for m in matches]
    times = [m.group(4) + ':' + m.group(5) + ':' + m.group(6) for m in matches]
    offsets = [m.group(7) for m in matches]

    prefix_parts = []
    compressed = list(parsed)

    all_same_date = len(set(dates)) == 1
    all_same_year = len(set(years)) == 1

    if all_same_date:
        prefix_parts.append(('date', dates[0]))
        for i, m in enumerate(matches):
            offset_part = offsets[i] if offsets[i] else ''
            compressed[i] = times[i] + offset_part
    elif all_same_year:
        prefix_parts.append(('year', years[0]))
        for i, m in enumerate(matches):
            offset_part = offsets[i] if offsets[i] else ''
            compressed[i] = m.group(2) + '-' + m.group(3) + 'T' + times[i] + offset_part

    non_none_offsets = [o for o in offsets if o is not None]
    if non_none_offsets and len(set(non_none_offsets)) == 1 and len(non_none_offsets) == len(offsets):
        shared_tz = non_none_offsets[0]
        prefix_parts.append(('tz', shared_tz))
        for i in range(len(compressed)):
            if compressed[i].endswith(shared_tz):
                compressed[i] = compressed[i][:-len(shared_tz)]

    seconds = [m.group(6) for m in matches]
    minutes = [m.group(5) for m in matches]
    all_zero_seconds = all(s == '00' for s in seconds)
    all_zero_minutes_seconds = all_zero_seconds and all(m == '00' for m in minutes)

    if all_zero_minutes_seconds:
        for i in range(len(compressed)):
            compressed[i] = re.sub(r'(\d{2}):00:00', r'\1h', compressed[i])
            compressed[i] = re.sub(r'(\d{2}):00$', r'\1h', compressed[i])
    elif all_zero_seconds:
        for i in range(len(compressed)):
            compressed[i] = re.sub(r':00([-+T])', r'\1', compressed[i])
            compressed[i] = re.sub(r':00$', '', compressed[i])

    if prefix_parts:
        prefix_line = '[' + ', '.join(f'{k}: {v}' for k, v in prefix_parts) + ']'
    else:
        prefix_line = None

    new_rows = []
    for i, row in enumerate(rows):
        new_row = list(row)
        new_row[ts_idx] = compressed[i]
        new_rows.append(new_row)

    return prefix_line, headers, new_rows


def fold_constant_columns(headers, rows):
    if len(rows) < FOLD_MIN_ROWS or not headers:
        return [], headers, rows

    keep_idx = []
    folded = []
    for i, h in enumerate(headers):
        first = rows[0][i]
        if all(row[i] == first for row in rows):
            folded.append((h, first))
        else:
            keep_idx.append(i)

    if not folded or not keep_idx:
        return [], headers, rows

    new_headers = [headers[i] for i in keep_idx]
    new_rows = [[row[i] for i in keep_idx] for row in rows]
    return folded, new_headers, new_rows


def format_table(headers, rows, truncated, total, max_cell):
    processed_rows = []
    for row in rows:
        processed = [truncate_cell(escape_cell(val), max_cell) for val in row]
        processed_rows.append(processed)

    prefix_line, headers, processed_rows = compress_timestamps(headers, processed_rows)
    folded, headers, processed_rows = fold_constant_columns(headers, processed_rows)

    lines = []
    if folded:
        folded_desc = ', '.join(f'{k}={v!r}' for k, v in folded)
        lines.append(
            f'[note: columns hidden from the table below because '
            f'all rows share the same value — {folded_desc}]'
        )
    if prefix_line:
        lines.append(prefix_line)

    header_line = '|' + '|'.join(f' {h} ' for h in headers) + '|'
    lines.append(header_line)
    sep_line = '|' + '|'.join('-' * (len(h) + 2) for h in headers) + '|'
    lines.append(sep_line)

    for row in processed_rows:
        row_line = '|' + '|'.join(f' {val} ' for val in row) + '|'
        lines.append(row_line)

    n = len(processed_rows)
    if truncated:
        lines.append(f'(showing {n} of {total} rows - add LIMIT or tighten WHERE clause)')
    else:
        lines.append(f'({n} row{"s" if n != 1 else ""})')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Read-only SQL query tool for aicontext.')
    parser.add_argument('sql', nargs='?', default=None, help='SQL query (or pass via stdin)')
    parser.add_argument('--db', default=DEFAULT_DB,
                        help=f'Database file in data/ (default: {DEFAULT_DB})')
    parser.add_argument('--max-cell', type=int, default=DEFAULT_MAX_CELL,
                        help=f'Max cell length (default {DEFAULT_MAX_CELL}, 0=no truncation)')
    args = parser.parse_args()

    if args.sql is not None:
        sql = args.sql.strip()
    elif not sys.stdin.isatty():
        import select
        if select.select([sys.stdin], [], [], 0.5)[0]:
            sql = sys.stdin.read().strip()
        else:
            print('Error: provide SQL as argument or via stdin', file=sys.stderr)
            sys.exit(1)
    else:
        print('Error: provide SQL as argument or via stdin', file=sys.stderr)
        sys.exit(1)

    if not sql:
        print('Error: empty query', file=sys.stderr)
        sys.exit(1)

    first_word = sql.split()[0].lower()
    if first_word in WRITE_KEYWORDS:
        print(f'Error: write operations not allowed (detected: {first_word.upper()})', file=sys.stderr)
        sys.exit(1)

    db_path = os.path.realpath(os.path.join(DATA_DIR, args.db))
    if not os.path.exists(db_path):
        print(f'Error: database not found at {db_path}', file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    conn.execute('PRAGMA busy_timeout = 30000')

    try:
        cursor = conn.execute(sql)
        if cursor.description is None:
            print('(query returned no result set)')
            return

        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS + 1)
        truncated = len(rows) > MAX_ROWS

        if truncated:
            total = conn.execute(f'SELECT COUNT(*) FROM ({sql})').fetchone()[0]
            rows = rows[:MAX_ROWS]
        else:
            total = len(rows)

        print(format_table(headers, rows, truncated, total, args.max_cell))

    except sqlite3.Error as e:
        print(f'SQL error: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
