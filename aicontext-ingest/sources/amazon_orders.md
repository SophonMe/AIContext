# Amazon Order History

## Overview

Amazon purchase history exported as CSV.

- **source**: `"amazon"`
- **service**: `"orders"`
- **action**: `"purchased"`
- **mode**: `static`

## Data Location

Exported from Amazon via "Download order reports" or "Request My Data".
Typically a CSV file named something like `Orders.csv`,
`Retail.OrderHistory.csv`, `01-Digital-Orders.csv`, or similar. May be
inside a directory of multiple Amazon export files. Scan for CSV files
whose headers suggest order data.

## Data Format

CSV with headers. Common column names (may vary by region/export method):

- **Product Name** / `Product Name` / `Title` / `Item Description`
- **Order Date** / `Order Date` / `Purchase Date`
- **Unit Price** / `Item Total` / `Total Owed` / `Price`
- **Currency** / `Currency Code`
- **Order ID** / `Order Number`
- **Quantity** / `Qty`
- **Category**

The exact column names vary between export methods (manual download vs
"Request My Data") and across regions. Match columns case-insensitively
and look for columns containing keywords like "product", "name", "date",
"price", "order", "quantity".

### Timestamp Format

Order dates may appear as:
- ISO 8601: `2026-03-15T10:30:00Z` or `2026-03-15`
- US format: `03/15/2026` or `March 15, 2026`
- Other locales: `15/03/2026` (DD/MM/YYYY)

Parse flexibly — try ISO first, then common date formats.

### Encoding

Amazon CSVs often use UTF-8 with BOM (`utf-8-sig`). Always try this encoding.

## What To Extract

- **title**: Product name
- **extra.price**: Unit price (float, strip currency symbols like `$`, `€`)
- **extra.currency**: Currency code (e.g., "USD", "EUR", "GBP")
- **extra.quantity**: Quantity if available and > 1
- **extra.order_id**: Order ID if available

## Edge Cases

- Rows with empty product names — skip
- Duplicate order IDs with different products are separate records
- Digital orders may be in a separate CSV file
- Some exports include headers repeated mid-file — handle gracefully
- Trailing empty rows — skip
