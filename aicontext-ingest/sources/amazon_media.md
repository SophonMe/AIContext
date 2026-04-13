# Amazon Media (Music & Prime Video)

## Overview

Amazon listening and viewing history exported as CSV files.

- **source**: `"amazon"`
- **mode**: `static`

This guide covers two related exports:
- **Amazon Music** → `service="music"`, `action="listened"`
- **Amazon Prime Video** → `service="prime_video"`, `action="watched"`

## Data Location

From Amazon's "Request My Data" export. Look for:
- Music: `Retail.ListeningHistory.csv`, `Amazon Music/`, or files with
  "Listen" in the name
- Video: `Retail.ViewingHistory.csv`, `Prime Video/`, or files with
  "Viewing" or "Watch" in the name

## Amazon Music Format

CSV with headers. Common columns:

- **Product Name** / `Title` / `Track Name` — song/album name
- **Date** / `Timestamp` — when listened
- **Listen Duration in Milliseconds** / `Duration` — playback duration
- **Device Type** / `Device` — playback device (optional)

### What To Extract

- **title**: Track/product name
- **extra.duration_millis**: Listen duration in milliseconds (integer)
- **extra.device_type**: Device (e.g., "Echo Dot", "Web Player")

### Filters

- Skip records with zero or missing duration (not actually listened)
- Skip records with empty product names

## Amazon Prime Video Format

CSV with headers. Common columns:

- **Title** / `Product Name` — video title
- **Material Type** / `Content Type` — type of content
- **Seconds Viewed** / `Duration` / `Watch Duration` — seconds watched
- **Playback Start Datetime (UTC)** / `Timestamp` / `Date` — when watched
- **Device Manufacturer Name** / `Device` — playback device (optional)
- **Content Quality** / `Quality` — HD, 4K, SD, etc. (optional)

### What To Extract

- **title**: Video title
- **extra.seconds_viewed**: Seconds watched (float/int)
- **extra.device**: Device manufacturer
- **extra.quality**: Content quality

### Filters

- Skip records with "Promo" or "Trailer" material type
- Skip records with zero or missing seconds viewed
- Skip records with empty titles

## Encoding

UTF-8 with BOM (`utf-8-sig`) for both.

## Timestamp Format

Typically ISO 8601 UTC for both. Parse flexibly.
