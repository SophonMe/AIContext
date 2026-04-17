#!/usr/bin/env python3
"""HTML viewer for the aicontext activity.db.

Delegates queries to the installed query.py (read-only) at
``~/.aicontext/skill/scripts/query.py``.

Usage:
    aicontext viewer [--port 8080]
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import subprocess
import sys
import webbrowser

AICONTEXT_DIR = os.path.expanduser("~/.aicontext")
DATA_DIR = os.path.join(AICONTEXT_DIR, "data")
SKILL_DIR = os.path.join(AICONTEXT_DIR, "skill")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
QUERY_SCRIPT = os.path.join(SCRIPTS_DIR, "query.py")
REF_DATA_DIR = os.path.join(DATA_DIR, "reference_data")
DB_PATH = os.path.join(DATA_DIR, "activity.db")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AIContext Viewer</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; }
.container { max-width: 1680px; margin: 0 auto; padding: 16px; }
h1 { font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #e6edf3; }

.stats { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px; min-width: 140px; }
.stat-card .label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-card .value { font-size: 22px; font-weight: 600; color: #58a6ff; margin-top: 2px; }

.filters { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.filters select, .filters input, .filters button {
  background: #161b22; border: 1px solid #30363d; border-radius: 6px;
  color: #c9d1d9; padding: 6px 10px; font-size: 13px; outline: none;
}
.filters select:focus, .filters input:focus { border-color: #58a6ff; }
.filters button { background: #238636; border-color: #238636; color: #fff; cursor: pointer; font-weight: 500; }
.filters button:hover { background: #2ea043; }
.filters button.secondary { background: #21262d; border-color: #30363d; color: #c9d1d9; }
.filters input[type="text"] { width: 200px; }
.filters input[type="date"] { width: 140px; }

.sql-bar { margin-bottom: 12px; display: flex; gap: 8px; }
.sql-bar input { flex: 1; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px;
  background: #161b22; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; padding: 8px 12px; }
.sql-bar input:focus { border-color: #58a6ff; }

.table-wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 6px; }
table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: 13px; }
thead { background: #161b22; position: sticky; top: 0; }
th { text-align: left; padding: 8px 10px; font-weight: 600; color: #8b949e; border-bottom: 1px solid #30363d;
  user-select: none; white-space: nowrap; position: relative; }
td { padding: 6px 10px; border-bottom: 1px solid #21262d; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tr:hover { background: #161b22; }
td.timestamp { color: #8b949e; font-family: monospace; font-size: 12px; white-space: nowrap; }
td.source { color: #d2a8ff; }
td.service { color: #79c0ff; }
td.action { color: #7ee787; }
td.title { color: #e6edf3; max-width: 500px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
td.extra { color: #8b949e; font-family: monospace; font-size: 11px; max-width: 300px; }
.col-resizer {
  position: absolute;
  top: 0;
  right: -3px;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
  z-index: 2;
}
.col-resizer:hover,
.col-resizer.active {
  background: rgba(88, 166, 255, 0.35);
}

.pagination { display: flex; gap: 8px; margin-top: 12px; align-items: center; justify-content: space-between; }
.pagination .info { color: #8b949e; font-size: 13px; }
.pagination button { background: #21262d; border: 1px solid #30363d; border-radius: 6px;
  color: #c9d1d9; padding: 6px 14px; cursor: pointer; font-size: 13px; }
.pagination button:hover { background: #30363d; }
.pagination button:disabled { opacity: 0.4; cursor: default; }

.detail-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 100; }
.detail-panel { position: fixed; top: 0; right: 0; width: 550px; height: 100vh; background: #161b22;
  border-left: 1px solid #30363d; z-index: 101; overflow-y: auto; padding: 20px; display: none; }
.detail-panel h2 { font-size: 16px; margin-bottom: 12px; color: #e6edf3; }
.detail-panel h3 { font-size: 14px; margin: 16px 0 8px; color: #58a6ff; border-top: 1px solid #30363d; padding-top: 12px; }
.detail-panel .field { margin-bottom: 10px; }
.detail-panel .field .label { font-size: 11px; color: #8b949e; text-transform: uppercase; margin-bottom: 2px; }
.detail-panel .field .value { font-size: 13px; color: #c9d1d9; word-break: break-all; }
.detail-panel .field .value a { color: #58a6ff; cursor: pointer; }
.detail-panel pre { background: #0d1117; padding: 10px; border-radius: 6px; font-size: 12px;
  overflow-x: auto; color: #c9d1d9; white-space: pre-wrap; word-break: break-all; }
.detail-panel .close-btn { position: absolute; top: 12px; right: 12px; background: none; border: none;
  color: #8b949e; font-size: 20px; cursor: pointer; }
.detail-panel .close-btn:hover { color: #e6edf3; }
.detail-panel .ref-data { margin-top: 8px; }

.tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #30363d; }
.tab { padding: 8px 16px; cursor: pointer; color: #8b949e; font-size: 13px; border-bottom: 2px solid transparent; }
.tab:hover { color: #e6edf3; }
.tab.active { color: #58a6ff; border-bottom-color: #58a6ff; }
.tab-content { display: none; }
.tab-content.active { display: block; }

.table-picker { margin-bottom: 12px; }
.table-picker select { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
  color: #c9d1d9; padding: 6px 10px; font-size: 13px; }
</style>
</head>
<body>
<div class="container">
  <h1>AIContext Viewer</h1>
  <div class="tabs">
    <div class="tab active" data-tab="browse">Browse</div>
    <div class="tab" data-tab="tables">Tables</div>
    <div class="tab" data-tab="sql">SQL</div>
  </div>

  <!-- Browse tab (activity table with filters) -->
  <div class="tab-content active" id="tab-browse">
    <div class="stats" id="stats"></div>
    <div class="filters">
      <select id="f-source"><option value="">All Sources</option></select>
      <select id="f-service"><option value="">All Services</option></select>
      <select id="f-action"><option value="">All Actions</option></select>
      <input type="text" id="f-search" placeholder="Search title...">
      <input type="date" id="f-from">
      <input type="date" id="f-to">
      <button onclick="applyFilters()">Filter</button>
      <button class="secondary" onclick="resetFilters()">Reset</button>
    </div>
    <div id="browse-prefix" style="margin-bottom:4px;color:#f0883e;font-family:monospace;font-size:12px;"></div>
    <div class="table-wrap"><table id="browse-table">
      <thead><tr>
        <th>Timestamp</th>
        <th>Source</th>
        <th>Service</th>
        <th>Action</th>
        <th>Title</th>
        <th>Extra</th>
        <th>Ref</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table></div>
    <div class="pagination">
      <div class="info" id="page-info"></div>
      <div><button id="btn-prev" onclick="prevPage()">Prev</button> <button id="btn-next" onclick="nextPage()">Next</button></div>
    </div>
  </div>

  <!-- Tables tab (browse any table) -->
  <div class="tab-content" id="tab-tables">
    <div class="table-picker">
      <label style="color:#8b949e;font-size:13px;margin-right:8px;">Table:</label>
      <select id="table-select" onchange="loadTableView()"></select>
    </div>
    <div id="tbl-prefix" style="margin-bottom:4px;color:#f0883e;font-family:monospace;font-size:12px;"></div>
    <div class="table-wrap"><table id="tables-table">
      <thead id="tbl-thead"><tr></tr></thead>
      <tbody id="tbl-tbody"></tbody>
    </table></div>
    <div class="pagination">
      <div class="info" id="tbl-page-info"></div>
      <div><button id="tbl-btn-prev" onclick="tblPrevPage()">Prev</button> <button id="tbl-btn-next" onclick="tblNextPage()">Next</button></div>
    </div>
  </div>

  <!-- SQL tab -->
  <div class="tab-content" id="tab-sql">
    <div class="sql-bar">
      <input type="text" id="sql-input" placeholder="SELECT * FROM activity WHERE service='search' ORDER BY timestamp DESC LIMIT 50"
             onkeydown="if(event.key==='Enter')runSQL()">
      <button onclick="runSQL()" style="background:#238636;border-color:#238636;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;">Run</button>
    </div>
    <div id="sql-prefix" style="margin-bottom:4px;color:#f0883e;font-family:monospace;font-size:12px;"></div>
    <div class="table-wrap"><table id="sql-table">
      <thead id="sql-thead"><tr></tr></thead>
      <tbody id="sql-tbody"></tbody>
    </table></div>
    <div class="info" id="sql-info" style="margin-top:8px;color:#8b949e;font-size:13px;"></div>
  </div>
</div>

<div class="detail-overlay" id="detail-overlay" onclick="closeDetail()"></div>
<div class="detail-panel" id="detail-panel">
  <button class="close-btn" onclick="closeDetail()">&times;</button>
  <div id="detail-content"></div>
</div>

<script>
const PAGE_SIZE = 100;
let currentPage = 0, totalRows = 0;
let tblPage = 0, tblTotal = 0, tblName = '';
const columnWidths = { browse: [], sql: [], tables: {} };
const DEFAULT_COLUMN_WIDTHS = {
  browse: [180, 90, 90, 90, 690, 260, 130],
  sql: [],
};
const TABLE_COLUMN_WIDTH_HINTS = {
  id: 90,
  timestamp: 180,
  source: 110,
  service: 120,
  action: 110,
  title: 520,
  extra: 260,
  ref_type: 90,
  ref_id: 420,
  key: 180,
  value: 240,
  summary: 360,
  description: 420,
  dtstart: 180,
  location: 240,
  created_at: 180,
  updated_at: 180,
  modified_at: 180,
  project_path: 220,
  git_branch: 140,
  calendar: 160,
  status: 120,
  rrule: 280,
  uid: 280,
};

// Tabs
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-' + t.dataset.tab).classList.add('active');
  });
});

async function api(sql) {
  const r = await fetch('/api/query', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({sql})});
  return r.json();
}
async function apiRef(refType, refId) {
  const r = await fetch('/api/ref', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ref_type:refType, ref_id:refId})});
  return r.json();
}
function esc(s) { if(s==null) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function trunc(s, n) { return s && s.length > n ? s.substring(0, n-3)+'...' : s; }

function defaultWidthForColumn(key, idx, headerText) {
  const name = String(headerText || '').trim().toLowerCase();
  if (typeof key === 'string' && DEFAULT_COLUMN_WIDTHS[key] && DEFAULT_COLUMN_WIDTHS[key][idx]) {
    return DEFAULT_COLUMN_WIDTHS[key][idx];
  }
  if (TABLE_COLUMN_WIDTH_HINTS[name]) return TABLE_COLUMN_WIDTH_HINTS[name];
  if (name.length >= 24) return 280;
  if (name.length >= 16) return 220;
  if (name.length >= 10) return 160;
  return 120;
}

function getWidthState(key) {
  if (typeof key === 'string') return columnWidths[key];
  if (key && key.group === 'tables') {
    if (!columnWidths.tables[key.name]) columnWidths.tables[key.name] = [];
    return columnWidths.tables[key.name];
  }
  return [];
}

function applyColumnWidths(table, widths) {
  if (!table || !widths) return;
  const rows = table.querySelectorAll('tr');
  rows.forEach(row => {
    Array.from(row.children).forEach((cell, idx) => {
      const width = widths[idx];
      if (width) cell.style.width = width + 'px';
    });
  });
}

function enableColumnResize(table, key) {
  if (!table) return;
  const widths = getWidthState(key);
  applyColumnWidths(table, widths);
  const headers = table.querySelectorAll('thead th');
  headers.forEach((th, idx) => {
    if (th.querySelector('.col-resizer')) return;
    if (!widths[idx]) widths[idx] = defaultWidthForColumn(key, idx, th.textContent);
    th.style.width = widths[idx] + 'px';
    const handle = document.createElement('div');
    handle.className = 'col-resizer';
    handle.addEventListener('mousedown', e => {
      e.preventDefault();
      e.stopPropagation();
      handle.classList.add('active');
      const startX = e.clientX;
      const startWidth = th.getBoundingClientRect().width;
      const move = ev => {
        const nextWidth = Math.max(80, Math.round(startWidth + (ev.clientX - startX)));
        widths[idx] = nextWidth;
        applyColumnWidths(table, widths);
      };
      const up = () => {
        handle.classList.remove('active');
        window.removeEventListener('mousemove', move);
        window.removeEventListener('mouseup', up);
      };
      window.addEventListener('mousemove', move);
      window.addEventListener('mouseup', up);
    });
    th.appendChild(handle);
  });
}

async function init() {
  // Stats
  const stats = await api("SELECT COUNT(*) as total, COUNT(DISTINCT source) as sources, COUNT(DISTINCT service) as services, MIN(SUBSTR(timestamp,1,10)) as earliest, MAX(SUBSTR(timestamp,1,10)) as latest FROM activity");
  if (stats.rows && stats.rows[0]) {
    const s = stats.rows[0];
    document.getElementById('stats').innerHTML =
      `<div class="stat-card"><div class="label">Records</div><div class="value">${Number(s[0]).toLocaleString()}</div></div>` +
      `<div class="stat-card"><div class="label">Sources</div><div class="value">${s[1]}</div></div>` +
      `<div class="stat-card"><div class="label">Services</div><div class="value">${s[2]}</div></div>` +
      `<div class="stat-card"><div class="label">Date Range</div><div class="value" style="font-size:14px">${s[3]} to ${s[4]}</div></div>`;
  }
  // Filter options
  for (const [id, sql] of [['f-source',"SELECT DISTINCT source FROM activity ORDER BY source"],
    ['f-service',"SELECT DISTINCT service FROM activity ORDER BY service"],
    ['f-action',"SELECT DISTINCT action FROM activity ORDER BY action"]]) {
    const d = await api(sql);
    d.rows.forEach(r => { document.getElementById(id).innerHTML += `<option value="${r[0]}">${r[0]}</option>`; });
  }
  // Table list
  const tables = await api("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");
  const sel = document.getElementById('table-select');
  sel.innerHTML = '';
  (tables.rows||[]).forEach(r => { sel.innerHTML += `<option value="${r[0]}">${r[0]}</option>`; });

  enableColumnResize(document.getElementById('browse-table'), 'browse');
  loadPage();
}

// === Browse tab ===
function buildWhere() {
  const p = [];
  const v = id => document.getElementById(id).value;
  if(v('f-source')) p.push(`source='${v('f-source')}'`);
  if(v('f-service')) p.push(`service='${v('f-service')}'`);
  if(v('f-action')) p.push(`action='${v('f-action')}'`);
  const s = v('f-search').trim();
  if(s) p.push(`title LIKE '%${s.replace(/'/g,"''")}%'`);
  if(v('f-from')) p.push(`timestamp >= '${v('f-from')}'`);
  if(v('f-to')) p.push(`timestamp < '${v('f-to')}T99'`);
  return p.length ? ' WHERE ' + p.join(' AND ') : '';
}

async function loadPage() {
  const w = buildWhere();
  totalRows = (await api(`SELECT COUNT(*) FROM activity${w}`)).rows[0][0];
  const offset = currentPage * PAGE_SIZE;
  const data = await api(`SELECT id, timestamp, source, service, action, title, extra, ref_type, ref_id FROM activity${w} ORDER BY timestamp DESC LIMIT ${PAGE_SIZE} OFFSET ${offset}`);
  document.getElementById('browse-prefix').textContent = data.prefix || '';
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  (data.rows||[]).forEach(r => {
    const [id,ts,source,service,action,title,extra,ref_type,ref_id] = r;
    const extraShort = esc(trunc(extra,50));
    const refBadge = ref_type === 'url'
      ? `<a href="${esc(ref_id)}" target="_blank" style="color:#58a6ff;font-size:11px" onclick="event.stopPropagation()">${esc(trunc(ref_id,40))}</a>`
      : ref_type ? `<span style="color:#f0883e;font-size:11px;cursor:pointer" title="${esc(ref_type)}:${esc(ref_id)}">${esc(ref_type)}</span>` : '';
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.onclick = () => showDetail(r);
    tr.innerHTML = `<td class="timestamp">${esc(ts)}</td><td class="source">${esc(source)}</td><td class="service">${esc(service)}</td><td class="action">${esc(action)}</td><td class="title" title="${esc(title)}">${esc(title)}</td><td class="extra" title="${esc(extra||'')}">${extraShort}</td><td>${refBadge}</td>`;
    tbody.appendChild(tr);
  });
  enableColumnResize(document.getElementById('browse-table'), 'browse');
  const totalPages = Math.ceil(totalRows/PAGE_SIZE);
  document.getElementById('page-info').textContent = totalRows ? `${offset+1}-${Math.min(offset+PAGE_SIZE,totalRows)} of ${totalRows.toLocaleString()} (page ${currentPage+1}/${totalPages})` : '0 records';
  document.getElementById('btn-prev').disabled = currentPage===0;
  document.getElementById('btn-next').disabled = offset+PAGE_SIZE>=totalRows;
}

function applyFilters(){currentPage=0;loadPage();}
function resetFilters(){['f-source','f-service','f-action'].forEach(id=>document.getElementById(id).value='');['f-search','f-from','f-to'].forEach(id=>document.getElementById(id).value='');currentPage=0;loadPage();}
function prevPage(){if(currentPage>0){currentPage--;loadPage();}}
function nextPage(){if((currentPage+1)*PAGE_SIZE<totalRows){currentPage++;loadPage();}}

// === Tables tab ===
async function loadTableView() {
  tblName = document.getElementById('table-select').value;
  tblPage = 0;
  await loadTablePage();
}
async function loadTablePage() {
  if(!tblName) return;
  tblTotal = (await api(`SELECT COUNT(*) FROM "${tblName}"`)).rows[0][0];
  const offset = tblPage * PAGE_SIZE;
  const data = await api(`SELECT * FROM "${tblName}" LIMIT ${PAGE_SIZE} OFFSET ${offset}`);
  document.getElementById('tbl-prefix').textContent = data.prefix || '';
  const cols = data.columns || [];
  document.getElementById('tbl-thead').innerHTML = '<tr>' + cols.map(c=>`<th>${esc(c)}</th>`).join('') + '</tr>';
  const tbody = document.getElementById('tbl-tbody');
  tbody.innerHTML = '';
  (data.rows||[]).forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = r.map((v,i) => {
      const s = v==null ? '' : String(v);
      return `<td title="${esc(s)}">${esc(trunc(s,80))}</td>`;
    }).join('');
    tbody.appendChild(tr);
  });
  enableColumnResize(document.getElementById('tables-table'), {group:'tables', name:tblName});
  const totalPages = Math.ceil(tblTotal/PAGE_SIZE);
  document.getElementById('tbl-page-info').textContent = tblTotal ? `${offset+1}-${Math.min(offset+PAGE_SIZE,tblTotal)} of ${tblTotal.toLocaleString()} (page ${tblPage+1}/${totalPages})` : '0 rows';
  document.getElementById('tbl-btn-prev').disabled = tblPage===0;
  document.getElementById('tbl-btn-next').disabled = offset+PAGE_SIZE>=tblTotal;
}
function tblPrevPage(){if(tblPage>0){tblPage--;loadTablePage();}}
function tblNextPage(){if((tblPage+1)*PAGE_SIZE<tblTotal){tblPage++;loadTablePage();}}

// === Detail panel ===
async function showDetail(row) {
  const [id,ts,source,service,action,title,extra,ref_type,ref_id] = row;
  let html = `<h2>Record #${id}</h2>`;
  const fields = [['Timestamp',ts],['Source',source],['Service',service],['Action',action],['Title',title]];
  fields.forEach(([l,v])=>{html+=`<div class="field"><div class="label">${l}</div><div class="value">${esc(v)}</div></div>`;});
  if(extra){
    try{html+=`<div class="field"><div class="label">Extra</div><pre>${esc(JSON.stringify(JSON.parse(extra),null,2))}</pre></div>`;}
    catch(e){html+=`<div class="field"><div class="label">Extra</div><pre>${esc(extra)}</pre></div>`;}
  }
  if(ref_type && ref_id) {
    html += `<h3>Reference (${esc(ref_type)})</h3>`;
    if(ref_type === 'url') {
      html += `<div class="field"><div class="label">URL</div><div class="value"><a href="${esc(ref_id)}" target="_blank" style="color:#58a6ff">${esc(ref_id)}</a></div></div>`;
    } else {
      html += `<div class="field"><div class="label">ref_id</div><div class="value">${esc(ref_id)}</div></div>`;
      html += `<div class="ref-data" id="ref-data-area"><em style="color:#8b949e">Loading...</em></div>`;
    }
  }
  document.getElementById('detail-content').innerHTML = html;
  document.getElementById('detail-panel').style.display='block';
  document.getElementById('detail-overlay').style.display='block';

  // Load reference data (skip for url refs)
  if(ref_type && ref_id && ref_type !== 'url') {
    const refData = await apiRef(ref_type, ref_id);
    const area = document.getElementById('ref-data-area');
    area.innerHTML = '';
    if(refData.error) {
      const em = document.createElement('em');
      em.style.color = '#f85149';
      em.textContent = refData.error;
      area.appendChild(em);
    } else if(refData.data !== undefined) {
      const text = typeof refData.data === 'string'
        ? refData.data
        : JSON.stringify(refData.data, null, 2);
      renderRefText(area, text);
    }
  }
}

const REF_PREVIEW_LIMIT = 200000;
function renderRefText(area, text) {
  const pre = document.createElement('pre');
  const truncated = text.length > REF_PREVIEW_LIMIT;
  pre.textContent = truncated ? text.slice(0, REF_PREVIEW_LIMIT) : text;
  area.appendChild(pre);
  if(truncated) {
    const note = document.createElement('div');
    note.style.cssText = 'margin-top:8px;color:#8b949e;font-size:12px;display:flex;gap:8px;align-items:center';
    const label = document.createElement('span');
    label.textContent = `Showing first ${REF_PREVIEW_LIMIT.toLocaleString()} of ${text.length.toLocaleString()} chars`;
    const btn = document.createElement('button');
    btn.textContent = 'Show full';
    btn.style.cssText = 'background:#21262d;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;padding:4px 10px;cursor:pointer;font-size:12px';
    btn.onclick = () => { pre.textContent = text; note.remove(); };
    note.appendChild(label);
    note.appendChild(btn);
    area.appendChild(note);
  }
}
function closeDetail(){document.getElementById('detail-panel').style.display='none';document.getElementById('detail-overlay').style.display='none';}

// === SQL tab ===
async function runSQL() {
  const sql = document.getElementById('sql-input').value.trim();
  if(!sql) return;
  const t0 = performance.now();
  const data = await api(sql);
  const elapsed = ((performance.now()-t0)/1000).toFixed(2);
  if(data.error){document.getElementById('sql-prefix').textContent='';document.getElementById('sql-info').textContent='Error: '+data.error;document.getElementById('sql-thead').innerHTML='';document.getElementById('sql-tbody').innerHTML='';return;}
  document.getElementById('sql-prefix').textContent=data.prefix||'';
  document.getElementById('sql-thead').innerHTML='<tr>'+(data.columns||[]).map(c=>`<th>${esc(c)}</th>`).join('')+'</tr>';
  const tbody=document.getElementById('sql-tbody');tbody.innerHTML='';
  (data.rows||[]).forEach(r=>{const tr=document.createElement('tr');tr.innerHTML=r.map(v=>`<td title="${esc(v==null?'':String(v))}">${esc(v==null?'':trunc(String(v),120))}</td>`).join('');tbody.appendChild(tr);});
  enableColumnResize(document.getElementById('sql-table'), 'sql');
  const info = data.footer ? `${data.footer} (${elapsed}s)` : `${(data.rows||[]).length} rows in ${elapsed}s`;
  document.getElementById('sql-info').textContent=info;
}

document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDetail();});
init();
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    query_script = None
    query_cwd = None
    ref_data_dir = None

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        if self.path == '/api/query':
            sql = body.get('sql', '').strip()
            try:
                result = subprocess.run(
                    [sys.executable, self.query_script, sql, '--max-cell', '0'],
                    capture_output=True, text=True, timeout=30,
                    cwd=self.query_cwd,
                )
                if result.returncode != 0:
                    self._json({'error': result.stderr.strip() or 'query failed'})
                    return
                columns, rows, prefix, footer = self._parse_query_output(result.stdout.strip())
                resp = {'columns': columns, 'rows': rows}
                if prefix:
                    resp['prefix'] = prefix
                if footer:
                    resp['footer'] = footer
                self._json(resp)
            except subprocess.TimeoutExpired:
                self._json({'error': 'query timed out (30s)'})
            except Exception as e:
                self._json({'error': str(e)})

        elif self.path == '/api/ref':
            ref_type = body.get('ref_type', '')
            ref_id = body.get('ref_id', '')
            self._handle_ref(ref_type, ref_id)

        else:
            self.send_error(404)

    def _handle_ref(self, ref_type, ref_id):
        """Resolve a ref_type/ref_id to its data."""
        if ref_type == 'local':
            path_part, suffix = ref_id.split('#', 1) if '#' in ref_id else (ref_id, '')
            file_path = os.path.join(self.ref_data_dir, path_part)
            file_path = os.path.realpath(file_path)
            ref_root = os.path.realpath(self.ref_data_dir)
            try:
                in_ref_root = os.path.commonpath([ref_root, file_path]) == ref_root
            except ValueError:
                in_ref_root = False
            if not in_ref_root:
                self._json({'error': 'invalid ref path'})
                return
            if not os.path.isfile(file_path):
                self._json({'error': f'file not found: {ref_id}'})
                return
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._json({'data': data})
            except Exception as e:
                self._json({'error': str(e)})

        elif ref_type == 'table':
            parts = ref_id.split('#', 1)
            if len(parts) != 2:
                self._json({'error': f'invalid table ref: {ref_id}'})
                return
            table_name, key_value = parts
            if not all(c.isalnum() or c == '_' for c in table_name):
                self._json({'error': f'invalid table name: {table_name}'})
                return
            escaped_key = key_value.replace("'", "''")
            try:
                result = subprocess.run(
                    [sys.executable, self.query_script,
                     f"PRAGMA table_info({table_name})",
                     '--max-cell', '0'],
                    capture_output=True, text=True, timeout=10,
                    cwd=self.query_cwd,
                )
                cols, rows, _, _ = self._parse_query_output(result.stdout.strip())
                if not rows:
                    self._json({'error': f'table not found: {table_name}'})
                    return
                pk_col = None
                for row in rows:
                    if len(row) >= 6 and row[5] == '1':
                        pk_col = row[1]
                        break
                if pk_col is None:
                    pk_col = rows[0][1]

                result2 = subprocess.run(
                    [sys.executable, self.query_script,
                     f"SELECT * FROM {table_name} WHERE \"{pk_col}\" = '{escaped_key}'",
                     '--max-cell', '0'],
                    capture_output=True, text=True, timeout=10,
                    cwd=self.query_cwd,
                )
                if result2.returncode != 0:
                    self._json({'error': result2.stderr.strip()})
                    return
                cols2, rows2, _, _ = self._parse_query_output(result2.stdout.strip())
                if rows2:
                    data = dict(zip(cols2, rows2[0]))
                    self._json({'data': data})
                else:
                    self._json({'error': f'no row found: {key_value}'})
            except Exception as e:
                self._json({'error': str(e)})

        elif ref_type == 'url':
            self._json({'data': ref_id})

        else:
            self._json({'error': f'unknown ref_type: {ref_type}'})

    @staticmethod
    def _split_pipe_row(line):
        """Split a pipe-separated row respecting \\| escapes."""
        inner = line.strip()
        if inner.startswith('|'):
            inner = inner[1:]
        if inner.endswith('|'):
            inner = inner[:-1]

        placeholder = '\x00'
        inner = inner.replace('\\\\', '\x01')
        inner = inner.replace('\\|', placeholder)
        parts = inner.split('|')
        cells = []
        for p in parts:
            p = p.strip()
            p = p.replace(placeholder, '|')
            p = p.replace('\\n', '\n')
            p = p.replace('\x01', '\\')
            cells.append(p)
        return cells

    @staticmethod
    def _parse_query_output(output):
        """Parse query.py output. Returns (columns, rows, prefix, footer)."""
        if not output:
            return [], [], None, None
        lines = output.split('\n')

        prefix_lines = []
        start = 0
        for i, line in enumerate(lines):
            if line.startswith('|'):
                start = i
                break
            if line.strip():
                prefix_lines.append(line.strip())

        if start >= len(lines):
            return [], [], '\n'.join(prefix_lines) if prefix_lines else None, None

        columns = Handler._split_pipe_row(lines[start])

        rows = []
        footer = None
        for line in lines[start + 2:]:
            if line.startswith('('):
                footer = line.strip()
                break
            if line.startswith('|'):
                rows.append(Handler._split_pipe_row(line))

        prefix = '\n'.join(prefix_lines) if prefix_lines else None
        return columns, rows, prefix, footer

    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        pass


def run(port: int = 8080) -> None:
    if not os.path.exists(QUERY_SCRIPT):
        print(f"Error: query script not found at {QUERY_SCRIPT}", file=sys.stderr)
        print("Run 'aicontext install' first.", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(DB_PATH):
        print(f"Error: database not found at {DB_PATH}", file=sys.stderr)
        print("Run 'aicontext install' first.", file=sys.stderr)
        sys.exit(1)

    Handler.query_script = QUERY_SCRIPT
    Handler.query_cwd = SKILL_DIR
    Handler.ref_data_dir = REF_DATA_DIR

    class ReuseServer(http.server.HTTPServer):
        allow_reuse_address = True

    server = ReuseServer(('127.0.0.1', port), Handler)
    url = f'http://127.0.0.1:{port}'
    print(f'Viewer: {url}')
    print(f'DB:     {DB_PATH}')
    print('Ctrl+C to stop')
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped')
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description='aicontext activity database viewer')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    run(port=args.port)


if __name__ == '__main__':
    main()
