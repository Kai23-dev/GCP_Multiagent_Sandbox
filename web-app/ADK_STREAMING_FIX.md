# ADK Agent Streaming Fix Summary

## Problem
The streaming endpoint (`/api/agent-engine-stream`) was not working with ADK agents. It was returning an AsyncGenerator object but not properly handling the session creation and streaming flow that ADK agents require.

## Root Cause
The streaming endpoint was missing the proper ADK agent flow:
1. Not creating sessions with `async_create_session`
2. Not using `async_stream_query` with the session
3. Not passing user email for authentication
4. Not properly parsing the SSE response

## Fixes Applied to `/api/agent-engine-stream/route.ts`

### 1. Added User Email Parameter
```typescript
async function* streamAgentResponse(
  message: string,
  agentId: string,
  userId: string,
  sessionId?: string,
  userAccessToken?: string,
  userEmail?: string  // Added this parameter
)
```

### 2. Implemented Proper ADK Session Flow
```typescript
if (isADKAgent) {
  // Step 1: Create session if needed
  if (!sessionIdToUse || sessionIdToUse.startsWith('session_')) {
    const createSessionResponse = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_create_session',
        input: {
          user_id: userEmail || userId  // Use email for ADK
        }
      })
    });

    // Parse session ID from response
    let sessionOutput = sessionData.output;
    if (typeof sessionOutput === 'string') {
      sessionOutput = JSON.parse(sessionOutput);
    }
    sessionIdToUse = sessionOutput?.id || sessionOutput?.session_id;
  }

  // Step 2: Query with session
  const streamResponse = await fetch(streamQueryUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      class_method: 'async_stream_query',
      input: {
        user_id: userEmail || userId,
        session_id: sessionIdToUse,
        message: message
      }
    })
  });
}
```

### 3. Fixed SSE Response Parsing
```typescript
if (responseText.includes('data:')) {
  const lines = responseText.split('\n');
  for (const line of lines) {
    if (line.startsWith('data:')) {
      const jsonStr = line.substring(5).trim();
      if (jsonStr && jsonStr !== '[DONE]') {
        const data = JSON.parse(jsonStr);
        // Extract text from various formats
        let text = data.content?.parts?.[0]?.text ||
                   data.text ||
                   data.message;
        if (text) {
          yield `data: {"type": "chunk", "content": "${text}"}\n\n`;
        }
      }
    }
  }
}
```

### 4. Updated Function Call
```typescript
// In POST handler
const res = streamAgentResponse(
  message,
  agentId,
  userId,
  currentSessionId,
  userAccessToken,
  userInfo.email  // Pass email from IAP headers
);
```

## Testing

### Local Testing
```bash
# Start the dev server
cd web-app
npm run dev

# Run the test script
node test-adk-agent.js
```

### Manual Testing with curl
```bash
# Test streaming endpoint
curl -X POST http://localhost:3000/api/agent-engine-stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "agentId": "1788443623507886080"
  }'
```

### Production Testing
When deployed to Cloud Run, the app will:
1. Use IAP headers to get the user's actual email
2. Create sessions with the email address
3. Maintain session context across messages

## Key Differences from Shell Script

The web app now mirrors the shell script behavior:

| Step | Shell Script | Web App (Fixed) |
|------|-------------|-----------------|
| 1. Create Session | `async_create_session` with email | ✅ Same |
| 2. Parse Session | Extract from `.output` field | ✅ Same logic |
| 3. Query | `async_stream_query` with session | ✅ Same |
| 4. User ID | Uses email address | ✅ Uses IAP email |
| 5. API Version | `v1beta1` | ✅ Already using |

## Files Modified
- `/web-app/src/app/api/agent-engine-stream/route.ts` - Fixed streaming endpoint
- `/web-app/src/app/api/agent-engine/route.ts` - Previously fixed
- `/web-app/src/app/api/agent-engine-correct/route.ts` - Previously fixed

## Environment Variables Required
```env
GOOGLE_CLOUD_PROJECT=sco-agents-np-9orx
GOOGLE_CLOUD_LOCATION=us-central1
```

## Next Steps
1. Deploy to Cloud Run
2. Verify IAP headers provide correct email
3. Test with multiple ADK agents
4. Monitor logs for session creation/usage

The streaming endpoint should now work exactly like the shell script!