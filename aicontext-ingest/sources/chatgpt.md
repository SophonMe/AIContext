# ChatGPT Conversation Export

## Overview

OpenAI ChatGPT conversations exported via "Export my data" in ChatGPT settings.

- **source**: `"openai"`
- **service**: `"chatgpt"`
- **actions**: `"prompted"` (user), `"received"` (assistant)
- **mode**: `static`

## Data Location

The export is a ZIP file or extracted directory. Inside, look for conversation
JSON files. Common structures:

```
chatgpt-export/
├── conversations.json          (single file with all conversations)
├── Conversations__001/         (or split into numbered directories)
│   ├── conversations-001.json
│   └── conversations-002.json
└── Conversations__001.zip      (may still be zipped)
```

The path may point to:
- A single `conversations.json` file
- A directory containing `Conversations__*/conversations-*.json`
- A directory containing `Conversations__*.zip` files (unzip first)

Discover which structure is present and handle accordingly.

## Data Format

Each conversation is a JSON object:

```json
{
  "id": "abc-123",
  "title": "How to cook pasta",
  "create_time": 1710000000.0,
  "update_time": 1710003600.0,
  "mapping": {
    "node-id-1": {
      "message": {
        "author": {"role": "user"},
        "content": {"parts": ["How do I cook pasta?"]},
        "create_time": 1710000000.0
      },
      "parent": null,
      "children": ["node-id-2"]
    },
    "node-id-2": {
      "message": {
        "author": {"role": "assistant"},
        "content": {"parts": ["Here's how to cook pasta..."]},
        "create_time": 1710000060.0,
        "metadata": {"model_slug": "gpt-4"}
      },
      "parent": "node-id-1",
      "children": []
    }
  }
}
```

### Message Structure

Messages are in a DAG (directed acyclic graph) via the `mapping` field.
Traverse from root (node with `parent=null`) following `children` links
(BFS or DFS). Each node has:

- `message.author.role`: `"user"`, `"assistant"`, `"system"`, `"tool"`
- `message.content.parts`: array of strings or objects with `"text"` key
- `message.create_time`: Unix timestamp (seconds, float)
- `message.metadata.model_slug`: model name (optional, for assistant messages)

### Conversation ID

Try `"id"` first, then `"conversation_id"` — both formats exist.

### Timestamp Format

`create_time` is Unix seconds (float, since epoch 1970). May have fractional
seconds.

## What To Extract

For each user/assistant message:
- **title**: Message text (joined from `content.parts`)
- **action**: `"prompted"` for user, `"received"` for assistant
- **extra.model**: Model slug for assistant messages (e.g., "gpt-4", "gpt-4o")

Skip messages with:
- Role other than "user" or "assistant" (system, tool messages)
- Empty or missing text
- Missing `create_time`

## Edge Cases

- `content.parts` can be an array of strings, array of objects with `text`
  key, or a single string — handle all forms
- Nodes without a `message` field — skip
- ZIP files may need to be extracted in-place
- Very long conversations may have deep DAG structures
- Model slug may be null or absent — omit from extra
