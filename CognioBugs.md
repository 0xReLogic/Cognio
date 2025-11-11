# Cognio MCP - Bug Reports & Feature Requests

**Date**: November 11, 2025  
**Tested Version**: v1.0.8  
**Tester**: Real-world usage with 15+ memories

---

## 🐛 CRITICAL BUGS

### 1. Search Exact Match Failure
**Severity**: HIGH  
**Status**: ❌ Broken

**Problem**:
- Exact keyword search returns 0 results
- IP addresses not found: `100.90.115.16` → 0 results
- Technical specs not found: `B2als v2 4GB` → 0 results
- Even though the data exists in memory

**Test Results**:
```
✅ WORKS:
- "XFCE desktop" → Found 2 (score 0.492, 0.427)
- "Azure free tier" → Found 5 (score 0.757 - 0.507)
- "Tailscale" → Found 2 (score 0.559, 0.523)

❌ FAILED:
- "100.90.115.16" (exact IP) → 0 results
- "B2als v2 4GB" (exact specs) → 0 results
- "rdpdemo VM 8GB B2ms" → 0 results
```

**Root Cause**:
- Semantic search (all-MiniLM-L12-v2) is optimized for natural language
- Poor performance on technical data (IPs, specs, numbers)
- Similarity threshold (0.4) too high for exact matches

**Suggested Fix**:
1. Implement hybrid search (semantic + keyword/exact match)
2. Add fallback to exact string matching if semantic returns 0
3. Lower similarity threshold for technical content
4. Consider better embedding model for technical data

---

### 2. ~~open_nodes Tool Always Fails~~ → FIXED: get_memory Tool Added
**Severity**: HIGH  
**Status**: ✅ FIXED

**Problem**:
- No way to retrieve full memory content by ID
- `list_memories` only shows truncated snippets
- Users couldn't read complete memory text

**Solution Implemented**:
1. **Added GET `/memory/{memory_id}` API endpoint** (src/main.py)
   - Returns full memory content with all metadata
   - Proper error handling for non-existent IDs (404)
   - Includes project, tags, timestamps
   
2. **Added `get_memory` MCP tool** (mcp-server/index.js)
   - Takes `memory_id` parameter
   - Returns formatted memory details with full text
   - Proper error handling and logging
   
3. **Added test coverage** (tests/test_api.py)
   - Test for successful memory retrieval
   - Test for 404 on non-existent memory
   - ✅ All tests passing

**Usage**:
```javascript
// MCP Tool
mcp_cognio_get_memory({ memory_id: "abc-123-def" })

// API Endpoint
GET http://localhost:8080/memory/{memory_id}
```

**Files Modified**:
- `src/main.py` - Added GET endpoint before DELETE endpoint
- `mcp-server/index.js` - Added tool definition and handler
- `mcp-server/README.md` - Added documentation
- `tests/test_api.py` - Added test case

**Test Results**:
```bash
$ pytest tests/test_api.py::test_get_memory -v
✅ PASSED - Memory retrieval works correctly
✅ PASSED - 404 error for non-existent memory
```

---

### 3. list_projects Tool Error
**Severity**: MEDIUM  
**Status**: ✅ FIXED

**Problem**:
```javascript
mcp_cognio_list_projects()
// Returns: Error: Cannot convert undefined or null to object
```

**Expected Behavior**:
- Should list all available projects
- Help users discover existing projects

**Suggested Fix**:
- Handle null/undefined projects gracefully
- Return empty array if no projects exist
- Add proper error handling

**Fix Implemented**:
- Read from `stats.memories_by_project` with null-safe handling
- Return JSON array `[{ "name": string, "count": number }]` or `[]` when empty
- Improved error handling and predictable output format

**Verification**:
`mcp_cognio_list_projects()` → returns `[ {"name":"Cognio", "count": 1 } ]` after saving sample memory.

---

## ⚠️ LIMITATIONS

### 4. list_memories Shows Only Snippets
**Severity**: MEDIUM  
**Status**: ✅ FIXED/ENHANCED

**Problem**:
- `list_memories` only shows preview/truncated text
- No way to read full memory content via MCP tools
- Users must export to file to read full content

**Current Workaround**:
- Use `export_memories` → read file manually
- Not ideal for programmatic access

**Suggested Enhancement**:
- Add parameter `full_text: boolean` to `list_memories`
- Or fix `open_nodes` to enable full text retrieval
- Add `get_memory_by_id` tool for direct access

**Fix Implemented**:
- Added `full_text: boolean` to MCP `list_memories` (no truncation when true)
- Added `get_memory` MCP tool to retrieve full memory by ID
- Corrected paging (`page`/`limit`) and tags filtering in MCP

**Usage**:
```
// Full text listing (MCP)
mcp_cognio_list_memories({ project: "Cognio", page: 1, limit: 10, full_text: true })

// Full memory by ID (MCP)
mcp_cognio_get_memory({ memory_id: "<id>" })
```

**Verification**:
- Listing shows full text when `full_text: true`
- `get_memory` returns complete content and metadata

---

## 🚀 FEATURE REQUESTS

### 5. Hybrid Search (Semantic + Keyword)
**Priority**: HIGH

**Description**:
Implement dual search strategy:
1. Try semantic search first
2. If results < threshold, fallback to keyword/exact match
3. Combine and rank results

**Benefits**:
- Best of both worlds
- Handles natural language AND technical data
- Better user experience

**Example**:
```javascript
search_memory({
  query: "100.90.115.16",
  mode: "hybrid" // auto, semantic, keyword
})
```

---

### 6. Configurable Similarity Threshold
**Priority**: MEDIUM

**Description**:
Allow users to adjust similarity threshold per search:

```javascript
search_memory({
  query: "Azure VM",
  similarity_threshold: 0.3 // default: 0.4
})
```

**Benefits**:
- More flexible search
- Users can tune for their use case
- Better for technical vs natural language content

---

### 7. Search Filters & Advanced Query
**Priority**: MEDIUM

**Description**:
Add more search capabilities:

```javascript
search_memory({
  query: "Azure",
  tags: ["deployment", "current-setup"],
  date_from: "2025-11-01",
  date_to: "2025-11-11",
  sort_by: "created_at" // score, created_at, updated_at
})
```

**Benefits**:
- More precise search results
- Better organization
- Time-based filtering

---

### 8. Bulk Operations
**Priority**: LOW

**Description**:
Add tools for bulk operations:

```javascript
// Bulk update tags
update_memory_tags({
  memory_ids: ["id1", "id2", "id3"],
  add_tags: ["new-tag"],
  remove_tags: ["old-tag"]
})

// Bulk delete
delete_memories({
  memory_ids: ["id1", "id2", "id3"]
})

// Bulk move to project
move_memories({
  memory_ids: ["id1", "id2"],
  target_project: "NewProject"
})
```

**Benefits**:
- Easier memory management
- Save time on repetitive tasks

---

### 9. Memory Versioning
**Priority**: LOW

**Description**:
Track memory changes over time:

```javascript
get_memory_history({
  memory_id: "abc123"
})
// Returns: [v1, v2, v3] with timestamps

restore_memory_version({
  memory_id: "abc123",
  version: 2
})
```

**Benefits**:
- Undo accidental changes
- Track knowledge evolution
- Better for collaborative use

---

### 10. Import Memories
**Priority**: MEDIUM

**Description**:
Currently only export works, add import:

```javascript
import_memories({
  file_path: "backup.json",
  project: "Azure-Expert-Knowledge",
  merge_strategy: "skip_duplicates" // overwrite, skip_duplicates, merge
})
```

**Benefits**:
- Backup & restore
- Share memories between instances
- Migration between servers

---

## 📊 PERFORMANCE SUGGESTIONS

### 11. Caching for Frequent Searches
**Priority**: LOW

**Description**:
- Cache search results for common queries
- Invalidate on memory updates
- Configurable TTL

**Benefits**:
- Faster repeated searches
- Reduced embedding computation
- Better UX

---

### 12. Batch Embedding Generation
**Priority**: LOW

**Description**:
- Generate embeddings in batches during save
- Async processing for large texts
- Progress indicator

**Benefits**:
- Faster save operations
- Better for bulk imports
- Non-blocking

---

## 🔧 DEVELOPER EXPERIENCE

### 13. Better Error Messages
**Priority**: MEDIUM

**Description**:
Current errors are vague:
- "Tool execution failed" → Why?
- "Cannot convert undefined or null to object" → Where?

**Suggested**:
- Add detailed error messages
- Include context (which field, what value)
- Suggest fixes

---

### 14. Debug Mode
**Priority**: LOW

**Description**:
Add debug flag to see internals:

```javascript
search_memory({
  query: "Azure",
  debug: true
})
// Returns: {
//   results: [...],
//   debug: {
//     embedding_time: "50ms",
//     search_time: "120ms",
//     similarity_scores: [0.8, 0.6, 0.4],
//     threshold_used: 0.4
//   }
// }
```

**Benefits**:
- Easier troubleshooting
- Performance optimization
- Better understanding of search behavior

---

## 📝 DOCUMENTATION REQUESTS

### 15. Search Best Practices
**Priority**: MEDIUM

**Topics Needed**:
- When to use semantic vs keyword search
- How to structure memory text for better search
- Optimal similarity threshold for different use cases
- Tag strategy recommendations

---

### 16. API Examples
**Priority**: MEDIUM

**Missing Examples**:
- Complex search queries
- Memory organization patterns
- Project management workflows
- Integration with other MCP servers

---

## 🎯 SUMMARY

**Critical Issues** (Fix ASAP):
1. ❌ Search exact match failure
2. ❌ open_nodes tool broken
3. ❌ list_projects error

**High Priority Features**:
1. 🚀 Hybrid search (semantic + keyword)
2. 🚀 Full text retrieval (fix open_nodes or add get_memory_by_id)
3. 🚀 Import memories

**Nice to Have**:
- Configurable similarity threshold
- Advanced search filters
- Bulk operations
- Memory versioning
- Better error messages

---

## 💡 TESTING NOTES

**Test Environment**:
- 15 memories in Azure-Expert-Knowledge project
- Mix of technical (IPs, specs) and natural language content
- Real-world usage scenario (Azure infrastructure documentation)

**What Works Well**:
- ✅ save_memory (reliable)
- ✅ delete_memory (works)
- ✅ export_memories (JSON & markdown)
- ✅ set/get active project
- ✅ Semantic search for natural language

**What Needs Work**:
- ❌ Exact match search
- ❌ open_nodes tool
- ❌ list_projects tool
- ⚠️ Full text retrieval

---

**Repo**: https://github.com/0xrelogic/cognio-mcp  
**Stars**: 45+ (but no issues reported yet!)  
**Potential**: HIGH (great concept, needs polish)
