# Amazon Search History

## Overview

Amazon search query history exported as CSV.

- **source**: `"amazon"`
- **service**: `"search"`
- **action**: `"searched"`
- **mode**: `static`

## Data Location

Typically a CSV file from Amazon's "Request My Data" export. May be named
`Search-Data.csv`, `Retail.Search-Data.csv`, or similar. Look for CSV files
with columns containing "Keywords" and "Search Time".

## Data Format

CSV with headers. Common columns:

- **Keywords** — the search query
- **First Search Time (GMT)** / `Search Time` / `Timestamp` — when the search happened
- **Device Category** / `Device Type` — device used (optional)
- **Number of Clicked Items** — engagement metric (optional)
- **Number of Items Added to Cart** — engagement metric (optional)
- **Number of Items Ordered** — conversion metric (optional)
- **Maximum Purchase Price** — highest price in resulting purchases (optional)

### Timestamp Format

Typically ISO 8601 UTC. Parse flexibly.

### Encoding

UTF-8 with BOM (`utf-8-sig`).

## What To Extract

- **title**: The search query (Keywords)
- **extra.device_type**: Device category (skip if empty or "Not Applicable")
- **extra.items_clicked**: Number of clicked items (integer, if > 0)
- **extra.items_carted**: Number added to cart (integer, if > 0)
- **extra.items_ordered**: Number ordered (integer, if > 0)
- **extra.max_price**: Maximum purchase price (float, skip if "Not Applicable")

## Edge Cases

- Rows with empty keywords — skip
- Fields with value "Not Applicable" or similar sentinel — treat as absent
