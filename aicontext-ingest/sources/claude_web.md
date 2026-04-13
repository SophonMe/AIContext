# Claude.ai Conversation Export

## Overview

Anthropic Claude web conversations exported via account settings.

- **source**: `"anthropic"`
- **service**: `"claude_web"`
- **actions**: `"prompted"` (human), `"received"` (assistant)
- **mode**: `static`

## Data Location

The export is typically a single JSON file named `conversations.json`.
May be inside an archive directory. The path should point to the JSON
file itself or a directory containing it.

## Data Format

The file contains a JSON array of conversation objects:

```json
[
  {
    "uuid": "conv-abc-123",
    "name": "Help with Python",
    "chat_messages": [
      {
        "sender": "human",
        "created_at": "2026-03-15T10:30:00.000Z",
        "content": [{"type": "text", "text": "How do I sort a list?"}]
      },
      {
        "sender": "assistant",
        "created_at": "2026-03-15T10:30:05.000Z",
        "content": [
          {"type": "thinking", "thinking": "..."},
          {"type": "text", "text": "Here's how to sort a list..."}
        ]
      }
    ]
  }
]
```

### Conversation ID

Try `"uuid"` first, then `"id"` — both formats exist across export versions.

### Message Content

**Human messages** have varying content formats:
- `content: [{"type": "text", "text": "..."}]` (list of typed blocks)
- `content: ["plain string"]` (list of strings)
- `content: "plain string"` (single string)
- May also have a `text` field directly on the message

Extract text defensively — try the typed block format first, fall back to
simpler forms.

**Assistant messages** have typed content blocks:
- `{"type": "text", "text": "..."}` — the actual response text
- `{"type": "thinking", "thinking": "..."}` — extended thinking (skip for title)
- `{"type": "tool_use", ...}` — tool calls (skip for title)
- `{"type": "tool_result", ...}` — tool results (skip for title)

Only extract `type="text"` blocks for the activity record title. Join
multiple text blocks with newlines.

### Timestamp Format

ISO 8601 UTC: `"2026-03-15T10:30:00.000Z"` or with timezone offset.
May have fractional seconds. Parse via `parse_iso_utc()`.

## What To Extract

For each human/assistant message:
- **title**: Message text (extracted as described above)
- **action**: `"prompted"` for human, `"received"` for assistant

Skip messages with:
- Sender other than "human" or "assistant"
- Empty text after extraction
- Missing `created_at`

## Edge Cases

- Conversations without a `name` — use "Untitled" or derive from first message
- Very large conversations — process all messages; dedup handles duplicates
- Export format may evolve — parse defensively
