# Amazon Cart History

## Overview

Amazon shopping cart activity exported as CSV.

- **source**: `"amazon"`
- **service**: `"cart"`
- **action**: `"carted"`
- **mode**: `static`

## Data Location

From Amazon's "Request My Data" export. May be named
`Retail.CartItems.csv`, `Cart-Items.csv`, or similar.

## Data Format

CSV with headers. Common columns:

- **Product Name** / `Item Description` / `Title` — product added
- **Date Added to Cart** / `Date` / `Timestamp` — when added
- **Cart List** / `List Type` — which list (e.g., default cart, save for later)

### Encoding

UTF-8 with BOM (`utf-8-sig`).

## What To Extract

- **title**: Product name
- **extra.cart_list**: Cart list name, lowercased (e.g., "default", "save for later")

## Edge Cases

- Rows with empty product names — skip
- Cart list may be empty — omit from extra
