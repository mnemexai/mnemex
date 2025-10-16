# Plan: Add Bear as Long-Term Memory Store

## Research Summary

**Bear Note-Taking App:**
- **Storage**: SQLite database at `~/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite`
- **API**: X-callback-url protocol for write operations (`bear://x-callback-url/create`, `/add-text`, etc.)
- **Linking**: Supports wikilinks `[[Note Title]]`, hashtags `#tag`, and backlinks
- **Best Practice**: Hybrid architecture - direct database reads (fast) + API writes (sync-safe for iCloud)
- **Existing MCP Servers**: Multiple implementations exist showing proven patterns

## Implementation Plan

### 1. Configuration (config.py)
**Add new configuration fields:**
- `bear_enabled: bool` - Enable Bear as LTM target (default: False)
- `bear_db_path: Path | None` - Path to Bear SQLite database (auto-detect from default location)
- `bear_api_token: str | None` - Bear API token for x-callback-url operations
- `bear_tag_prefix: str` - Tag prefix for promoted memories (default: "mnemex")
- Keep existing Obsidian config fields for backward compatibility

**Environment Variables:**
- `MNEMEX_BEAR_ENABLED` - Enable Bear integration
- `MNEMEX_BEAR_DB_PATH` - Override default database path
- `MNEMEX_BEAR_API_TOKEN` - API token for write operations
- `MNEMEX_BEAR_TAG_PREFIX` - Tag prefix

### 2. Bear Database Reader (storage/bear_reader.py)
**Purpose**: Fast read-only access to Bear's SQLite database

**Key Components:**
- `BearNote` dataclass - Represent a Bear note (id, title, text, tags, created, modified)
- `BearReader` class - SQLite query interface
  - `get_notes()` - List all notes with optional tag filter
  - `search_notes(query, tags)` - Full-text search
  - `get_note_by_id(note_id)` - Retrieve specific note
  - `get_note_by_title(title)` - Find by title
  - `get_all_tags()` - List all tags
  - Auto-detect database at default location

**SQL Queries:**
- Query `ZSFNOTE` table for note content
- Query `ZSFNOTETAG` for tag relationships
- Handle Bear's polar markup (image references like `[assets/image1.png]`)

**Error Handling:**
- Gracefully handle database lock scenarios (SQLite busy/locked)
- Handle corrupted database files without crashing
- Return clear error messages for debugging
- Use read-only connection mode to prevent accidental writes
- Implement connection timeouts to avoid hanging

### 3. Bear X-Callback-URL Writer (integration/bear_writer.py)
**Purpose**: Safe write operations via Bear's official API

**Dependencies:**
- Use `python-xcall` library (add to pyproject.toml) or implement simple subprocess+urllib wrapper
- Requires Bear API token from user

**Key Methods:**
- `create_note(title, text, tags)` - Create new note, returns note ID
  - For large content (>2000 chars): Create with title only, then append content
  - Avoids OS-level URL length limits that could cause silent failures
- `add_text_to_note(note_id, text, mode='append')` - Append/prepend to existing note
- `add_tags_to_note(note_id, tags)` - Add tags to note
- `open_note(note_id)` - Open note in Bear (for verification)

**X-Callback-URL Format:**
```python
bear://x-callback-url/create?title={title}&text={text}&tags={tags}&token={api_token}
```

**Retry & Error Handling:**
- Implement retry mechanism (3 attempts with exponential backoff)
- Handle timeouts when Bear is slow or not running
- Return detailed status object: `{success: bool, note_id: str|None, error: str|None, timeout: bool}`
- Validate Bear is running before attempting callback
- Log failed callbacks for debugging

### 4. Bear Index (storage/bear_index.py)
**Purpose**: In-memory index of Bear notes for fast unified search

**Similar to LTMIndex but for Bear:**
- `BearDocument` - Similar to `LTMDocument`
- `BearIndex` class
  - Load notes from database via `BearReader`
  - Build in-memory index with title, content, tags
  - `search(query, tags, limit)` - Search interface matching `LTMIndex.search()`
  - `title_exists(title)` - Fast O(1) lookup for title uniqueness checking
  - Support incremental updates (check modified timestamps)
  - Cache index to avoid repeated database reads

**Storage:**
- Optional JSONL cache at `~/.config/mnemex/bear-index.jsonl`
- Refresh on demand or when notes modified

### 5. Bear Integration (integration/bear_integration.py)
**Purpose**: Unified interface for Bear promotion (mirroring BasicMemoryIntegration)

**Key Methods:**
- `is_available()` - Check if Bear database exists and API token configured
- `promote_to_bear(memory)` - Create Bear note from Memory object
  - Format memory content as markdown
  - Add metadata in note (created, last_used, use_count, STM ID)
  - Add tags (combine memory tags + configurable prefix like `#mnemex`)
  - **Ensure unique titles**: Append timestamp or STM ID suffix if title collision detected
  - Return note ID and success status
- `get_bear_stats()` - Count notes with mnemex tag prefix

**Note Title Strategy:**
- Primary: Use first 50 chars of content as title
- Uniqueness check: Check against in-memory Bear Index (Section 4) for existing titles
  - Much faster than direct database queries
  - Reduces load on SQLite database
  - Index already loaded for search operations
- Collision handling: Append `[{timestamp}]` or `[{stm_id[:8]}]` to ensure uniqueness
- Prevents user confusion from multiple notes with identical titles

**Note Format:**
```markdown
# {Memory Content Preview} [{unique_suffix_if_needed}]

{Full Memory Content}

---

**Metadata**
- Created: {date}
- Last Used: {date}
- Use Count: {count}
- STM ID: {uuid}
- Promoted: {date}

#mnemex #tag1 #tag2
```

### 6. Update Promote Tool (tools/promote.py)
**Modify existing tool to support Bear:**
- Add `target` validation for both "obsidian" and "bear"
- Branch logic:
  ```python
  if target == "obsidian":
      result = integration.promote_to_obsidian(candidate.memory)
  elif target == "bear":
      result = bear_integration.promote_to_bear(candidate.memory)
  ```
- Update `promoted_to` field with Bear note ID/URL

### 7. Update Unified Search (tools/search_unified.py)
**Add Bear to search sources:**
- After LTM search block, add Bear search block:
  ```python
  # Search Bear
  if config.bear_enabled and bear_db_exists:
      bear_index = BearIndex(...)
      bear_docs = bear_index.search(query, tags, limit*2)
      # Convert to UnifiedSearchResult with source="bear"
  ```
- Add `bear_weight` parameter (similar to `ltm_weight`)
- Merge Bear results into unified results list
- Deduplicate across STM, LTM (Obsidian), and Bear

### 8. Configuration Helpers
**Add to config.py or new util:**
- `detect_bear_database()` - Auto-find Bear DB (robust detection)
  - **Dynamic detection**: Scan `~/Library/Group Containers` for pattern `*.net.shinyfrog.bear`
  - Avoids hardcoding group container ID (differs between App Store/Setapp versions)
  - Future-proof against Bear app updates that change container ID
  - Returns first matching database path or None
- `validate_bear_token()` - Test API token with simple callback
- `get_bear_api_token_instructions()` - Return help text for finding token

### 9. Documentation
**New files to create:**
- `docs/bear-integration.md` - Complete Bear integration guide
  - How to get API token (Help → Advanced → API Token)
  - Configuration examples
  - Comparison with Obsidian integration
  - Limitations (macOS only, requires Bear installed)

**Update existing docs:**
- `README.md` - Add Bear to LTM options
- `CLAUDE.md` - Document Bear as alternative LTM target
- `.env.example` - Add Bear config variables

### 10. Testing
**New test files:**
- `tests/test_bear_reader.py` - Mock SQLite database, test queries
- `tests/test_bear_writer.py` - Mock x-callback-url calls
- `tests/test_bear_integration.py` - Test promotion flow
- `tests/test_search_unified_bear.py` - Test Bear in unified search

**Test Strategy:**
- Mock Bear database with test data
- Mock subprocess calls for x-callback-url
- Integration test with real Bear (optional, manual)

### 11. Dependencies
**Add to pyproject.toml:**
```toml
[project.optional-dependencies]
bear = [
    "python-xcall>=2.0.0",  # For x-callback-url on macOS
]
```

**Or**: Implement lightweight x-callback-url wrapper using stdlib (subprocess + urllib)

## Implementation Order

1. ✅ Configuration (config.py) - Foundation
2. ✅ Bear Database Reader (storage/bear_reader.py) - Read capability
3. ✅ Bear Writer (integration/bear_writer.py) - Write capability
4. ✅ Bear Integration (integration/bear_integration.py) - Promotion logic
5. ✅ Update Promote Tool (tools/promote.py) - Expose Bear as target
6. ✅ Bear Index (storage/bear_index.py) - Search capability
7. ✅ Update Unified Search (tools/search_unified.py) - Include Bear results
8. ✅ Tests - Ensure reliability
9. ✅ Documentation - User guide

## Key Design Decisions

**Why Hybrid Architecture?**
- Read from SQLite: Fast, no latency, efficient for search
- Write via API: Sync-safe, respects iCloud, official method

**Why Not Modify Bear Database Directly?**
- Bear uses iCloud sync - direct writes could corrupt sync state
- API is officially supported and guaranteed stable
- Follows best practices from existing Bear MCP servers

**Backward Compatibility:**
- All Obsidian functionality remains unchanged
- Bear is opt-in via configuration
- Both can be enabled simultaneously
- Users can promote to both targets

**Platform Limitation:**
- Bear is macOS/iOS only (SQLite path is macOS-specific)
- Detect platform and gracefully disable if not macOS
- Document this limitation clearly

## Success Criteria

- ✅ Can promote STM memories to Bear notes via `promote_memory(target="bear")`
- ✅ Bear notes appear in `search_unified()` results
- ✅ Existing Obsidian integration continues to work
- ✅ Configuration validates Bear availability before enabling
- ✅ Tests cover all Bear operations with mocks
- ✅ Documentation explains setup and usage clearly

## Code Review Improvements

After initial review, the following improvements were identified and incorporated:

1. **URL Length Limits (Section 3)**
   - Large memory content could exceed OS URL length limits
   - Solution: Create note with title only, then append content via `add_text_to_note()`
   - Prevents silent data loss from failed x-callback-url calls

2. **Dynamic Database Detection (Section 8)**
   - Hardcoded group container ID `9K33E3U3T4` is brittle
   - Different between App Store/Setapp versions
   - Solution: Scan for pattern `*.net.shinyfrog.bear` instead
   - More robust and future-proof

3. **Database Error Handling (Section 2)**
   - Explicit error handling for SQLite operations
   - Handle locked, busy, or corrupted databases gracefully
   - Prevent application crashes from database issues

4. **X-Callback-URL Retry Logic (Section 3)**
   - Handle timeouts when Bear is slow or not running
   - Implement retry mechanism with exponential backoff
   - Return detailed status objects for debugging

5. **Unique Note Titles (Section 5)**
   - Multiple memories with similar content could create duplicate titles
   - Confusing for users even though Bear allows it
   - Solution: Check for existing titles and append unique suffix (timestamp or STM ID)

6. **Efficient Title Uniqueness Check (Section 5)**
  - Direct database queries for title checking would be slow
  - Adds unnecessary load to SQLite database
  - Solution: Use in-memory Bear Index (Section 4) for title lookups
  - Much faster and index already loaded for search operations

## Research Links

- **Bear MCP Servers**:
  - [bejaminjones/bear-notes-mcp](https://github.com/bejaminjones/bear-notes-mcp) - Hybrid architecture reference
  - [akseyh/bear-mcp-server](https://github.com/akseyh/bear-mcp-server) - SQLite query examples
  - [jkawamoto/mcp-bear](https://github.com/jkawamoto/mcp-bear) - API token usage

- **Bear Documentation**:
  - [X-callback-url Scheme](https://bear.app/faq/x-callback-url-scheme-documentation/)
  - [Bear Database Location](https://bear.app/faq/where-are-bears-notes-located/)

- **Python Libraries**:
  - [python-xcall](https://github.com/robwalton/python-xcall) - X-callback-url for macOS
  - [bear-backlinks xcall.py](https://github.com/cdzombak/bear-backlinks/blob/master/xcall.py) - Simple implementation example
