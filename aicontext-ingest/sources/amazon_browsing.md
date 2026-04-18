# Amazon Browsing History

## Overview

Amazon product browsing/viewing history exported as CSV.

- **source_key**: `"amazon_browsing"`
- **source**: `"amazon"`
- **service**: `"browsing"`
- **action**: `"visited"`
- **mode**: `static`

## Data Location

From Amazon's "Request My Data" export. May be named
`Request All Your Data.Detail Page Glance View Impressions.csv`, or similar.

## Data Format

CSV with headers. Common columns:

- **product_name** / `Product Name` / `Title` — product viewed
- **creation_date** / `Date` / `Timestamp` — when viewed
- **website_list_price** / `Price` — product price (optional)
- **website_list_price_currency_code** / `Currency` — currency (optional)
- **device_type** / `Device` — device used (optional)

Note: Amazon exports may use lowercase_underscore or Title Case headers
depending on the export method. Match flexibly.

### Encoding

UTF-8 with BOM (`utf-8-sig`).

## What To Extract

- **title**: Product name
- **extra.price**: Price (float, if parseable)
- **extra.currency**: Currency code
- **extra.device_type**: Device type (e.g., "Mobile", "Desktop")

## Edge Cases

- Rows with empty product names — skip
- Price may be empty or unparseable — omit from extra
