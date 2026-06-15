# Memory Bank Debugging Guide

## Issue Fixed: Memory Search Not Working

### Problem
- Memory save was working
- Memory search returned empty arrays
- Memories weren't displaying in the browser

### Root Causes

#### 1. **API Response Structure Mismatch**
ADK returns memories in `result.output.memories`, not `result.memories` directly.

**Before:**
```typescript
const result = await response.json();
return { memories: result.memories || [] }; // ❌ Wrong path
```

**After:**
```typescript
const result = await response.json();
const memories = result.output?.memories || result.memories || []; // ✅ Correct
return { memories };
```

#### 2. **Session Data Format**
When saving to memory, ADK expects the session object from `sessionData.output`, not the full response.

**Before:**
```typescript
const saveResponse = await fetch(queryUrl, {
  body: JSON.stringify({
    class_method: 'async_add_session_to_memory',
    input: { session: sessionData } // ❌ Full response
  })
});
```

**After:**
```typescript
const session = sessionData.output || sessionData; // ✅ Extract session object
const saveResponse = await fetch(queryUrl, {
  body: JSON.stringify({
    class_method: 'async_add_session_to_memory',
    input: { session } // ✅ Correct format
  })
});
```

#### 3. **Memory Display Flexibility**
Memory objects can have different structures. The UI now handles variations.

**Features:**
- Handles `memory.memory` or direct `memory` object
- Supports multiple content fields: `content`, `text`, `summary`
- Displays relevance score if available
- Shows debug info in development mode

## How to Debug Memory Issues

### 1. Check Backend Logs

The API now logs detailed information:

```bash
# Watch logs while testing
npm run dev

# You'll see:
- "Getting session: user_id=..., session_id=..."
- "Retrieved session data: {...}"
- "Saving session to memory: {...}"
- "✅ Session saved to memory successfully"
- "Search result: {...}"
- "Found N memories"
```

### 2. Use Browser Console

Frontend logs are enabled:

```javascript
// When searching memories
console.log('Memory search response:', result);
console.log('Loaded N memories');

// When saving
console.log('Session ID set from stream:', sessionId);
```

### 3. Check Dev Debug Panel

In development mode, each memory card has a debug panel:

```html
<details>
  <summary>Debug Info</summary>
  <pre>{JSON.stringify(memory, null, 2)}</pre>
</details>
```

This shows the **raw memory structure** from ADK.

### 4. Test API Directly

#### Save Memory:
```bash
curl -X POST http://localhost:3000/api/agent-memory \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "4992860311498260480",
    "sessionId": "your-session-id",
    "action": "save"
  }'
```

#### Search Memories:
```bash
curl -X POST http://localhost:3000/api/agent-memory \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "4992860311498260480",
    "action": "search",
    "query": "test"
  }'
```

### 5. Test ADK Directly

```bash
# Get session
curl -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -X POST "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/PROJECT/locations/us-central1/reasoningEngines/AGENT_ID:query" \
  -H "Content-Type: application/json" \
  -d '{
    "class_method": "async_get_session",
    "input": {
      "user_id": "user@example.com",
      "session_id": "SESSION_ID"
    }
  }'

# Search memories
curl -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -X POST "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/PROJECT/locations/us-central1/reasoningEngines/AGENT_ID:query" \
  -H "Content-Type: application/json" \
  -d '{
    "class_method": "async_search_memory",
    "input": {
      "user_id": "user@example.com",
      "query": "test query"
    }
  }'
```

## Common Issues & Solutions

### "No memories found" after saving

**Possible Causes:**
1. Session wasn't saved correctly
2. Search query doesn't match saved content
3. User ID mismatch between save and search

**Debug Steps:**
1. Check logs for "✅ Session saved to memory successfully"
2. Try a broader search query (e.g., "conversation")
3. Check that user email is consistent

### Empty memories array

**Possible Causes:**
1. No memories have been saved yet
2. Response structure changed
3. ADK agent doesn't have memory enabled

**Debug Steps:**
1. Save a conversation first
2. Check raw API response in browser console
3. Verify ADK agent has `async_search_memory` method

### Session not found when saving

**Possible Causes:**
1. Session ID not captured from streaming
2. Session expired
3. Wrong session ID format

**Debug Steps:**
1. Check console for "Session ID set from stream"
2. Verify `sessionId` state in React DevTools
3. Start a new conversation and try again

## Expected Memory Flow

### Save Flow:
```
1. User chats with Agent Engine (streaming)
   └─> sessionId captured in frontend

2. User clicks "Save to Memory"
   └─> POST /api/agent-memory {action: 'save', sessionId}

3. Backend calls async_get_session
   └─> Retrieves full session data

4. Backend calls async_add_session_to_memory
   └─> Saves to ADK memory

5. Success message shown
   └─> "🧠 Session saved to Memory Bank!"
```

### Search Flow:
```
1. User clicks "Memory Browser"
   └─> Modal opens

2. User enters search query
   └─> POST /api/agent-memory {action: 'search', query}

3. Backend calls async_search_memory
   └─> Returns matching memories

4. Memories displayed in cards
   └─> With relevance scores
```

## ADK Memory Response Structures

### async_get_session response:
```json
{
  "output": {
    "id": "12345",
    "user_id": "user@example.com",
    "messages": [...],
    "state": {...}
  }
}
```

### async_add_session_to_memory response:
```json
{
  "output": {
    "memory_id": "mem_12345",
    "status": "saved"
  }
}
```

### async_search_memory response:
```json
{
  "output": {
    "memories": [
      {
        "content": "...",
        "relevance_score": 0.95,
        "timestamp": "2025-10-17T12:00:00Z"
      }
    ]
  }
}
```

## Verification Checklist

After implementing fixes:

- [ ] Session ID captured after streaming conversation
- [ ] "Save to Memory" button works without errors
- [ ] Success message appears in chat
- [ ] Memory Browser opens without errors
- [ ] Search returns saved memories
- [ ] Memory cards display correctly
- [ ] Relevance scores shown
- [ ] Debug info available in dev mode
- [ ] Logs show detailed information
- [ ] No console errors

## Performance Notes

- **Save operation:** ~2-3 seconds (depends on session size)
- **Search operation:** ~1-2 seconds (depends on memory count)
- **UI updates:** Instant (React state updates)

## Next Steps for Production

1. **Error Handling:** Add user-friendly error messages
2. **Loading States:** Better visual feedback during operations
3. **Pagination:** Handle large numbers of memories
4. **Filtering:** Add date/relevance filters
5. **Export:** Allow downloading memories
6. **Delete:** Add ability to remove memories
