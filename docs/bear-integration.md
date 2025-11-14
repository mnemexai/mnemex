# Bear Integration for Long-Term Memory

CortexGraph can use the [Bear note-taking app](https://bear.app/) as a long-term memory (LTM) store, providing a powerful alternative to the default Obsidian integration. This guide explains how to set it up and use it.

## Overview

The Bear integration uses a hybrid architecture for optimal performance and safety:
- **Fast Reads**: It reads directly from Bear's local SQLite database for high-speed searching and indexing.
- **Safe Writes**: It uses Bear's official `x-callback-url` API for creating and modifying notes, ensuring full compatibility with iCloud sync.

**Platform Limitation:** Please note that Bear is only available on macOS and iOS. This integration will only work on **macOS**.

## Configuration

To enable the Bear integration, you need to configure a few settings in your `.env` file.

First, copy the example environment file if you haven't already:
```bash
cp .env.example .env
```

Next, add the following variables to your `.env` file:

```bash
# --- Bear LTM Integration ---

# Enable Bear as an LTM target (default: false)
CORTEXGRAPH_BEAR_ENABLED=true

# Bear API Token (required for writing notes)
# See instructions below on how to get your token.
CORTEXGRAPH_BEAR_API_TOKEN="YOUR_BEAR_API_TOKEN"

# [Optional] Override the default path to Bear's database.
# The system auto-detects the path, so this is usually not needed.
# CORTEXGRAPH_BEAR_DB_PATH="/path/to/your/database.sqlite"

# [Optional] A tag prefix for all memories promoted to Bear.
# This helps organize and identify CortexGraph-generated notes.
CORTEXGRAPH_BEAR_TAG_PREFIX="cortexgraph"
```

### How to Get Your Bear API Token

1.  Open the Bear app on your Mac.
2.  Go to the **Help** menu.
3.  Navigate to **Advanced**.
4.  Click on **API Token**.
5.  Copy the token and paste it into your `.env` file.

## Usage

Once configured, you can promote memories to Bear using the `promote_memory` tool.

### Promoting a Memory to Bear

To promote a memory, specify `"bear"` as the `target`.

**MCP Tool Request:**
```json
{
  "tool_name": "promote_memory",
  "arguments": {
    "memory_id": "mem-12345abc",
    "target": "bear"
  }
}
```

This will create a new note in Bear with the memory's content and associated metadata.

### Unified Search

When `CORTEXGRAPH_BEAR_ENABLED` is set to `true`, the `search_unified` tool will automatically include Bear notes in its search results, alongside short-term memories and Obsidian notes.

## Note Format in Bear

When a memory is promoted, it is formatted as a Markdown note with the following structure:

```markdown
# {A short preview of the memory content}

{The full content of the memory goes here.}

---

**Metadata**
- Created: 2025-10-17 09:30:00
- Last Used: 2025-10-17 09:30:00
- Use Count: 5
- STM ID: mem-12345abc-6789-def0
- Promoted: 2025-10-17 09:35:00

#cortexgraph #memory_tag_1 #memory_tag_2
```

- **Title**: A unique title is generated from the memory's content. If a note with the same title already exists, a timestamp is added to prevent duplicates.
- **Metadata**: Key information about the memory is preserved for context.
- **Tags**: The memory's original tags are included, along with the global prefix (`#cortexgraph` by default).

## Comparison with Obsidian Integration

| Feature | Bear Integration | Obsidian Integration |
| :--- | :--- | :--- |
| **Platform** | macOS only | Cross-platform (macOS, Windows, Linux) |
| **Storage** | Centralized SQLite Database | Folder of individual Markdown files |
| **Sync** | iCloud (managed by Bear app) | User's choice (Obsidian Sync, iCloud, Git, etc.) |
| **Setup** | Requires API Token | Requires path to Obsidian Vault |
| **Performance** | Very fast reads via direct DB access | Fast reads, depends on file system speed |

Both integrations can be enabled and used simultaneously. You can choose where to promote each memory on a case-by-case basis.
