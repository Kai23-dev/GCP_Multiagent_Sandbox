# ADK Agent Integration Fix Summary

## Problem
The web app couldn't properly invoke ADK agents deployed to Agent Engine. The shell script (`test.sh`) was working, but the Node.js implementation had several issues.

## Root Causes Identified

1. **Incorrect JSON in requests** - Trailing commas breaking JSON parsing
2. **Session ID extraction** - Not parsing the nested session ID correctly from the response
3. **User ID mismatch** - Using generic user IDs instead of email addresses for ADK agents
4. **Variable interpolation** - Shell script variables not being properly substituted

## Fixes Applied

### 1. Fixed Session Creation (`agent-engine/route.ts` and `agent-engine-correct/route.ts`)

**Before:**
```typescript
sessionIdToUse = sessionData.output?.id || sessionData.output?.sessionId;
```

**After:**
```typescript
// Parse session ID from various possible locations
let sessionOutput = sessionData.output;

if (typeof sessionOutput === 'string') {
  try {
    sessionOutput = JSON.parse(sessionOutput);
  } catch {
    // If it's not JSON, use as is
  }
}

sessionIdToUse = sessionOutput?.id ||
                sessionOutput?.session_id ||
                sessionOutput?.sessionId ||
                sessionData.output?.id ||
                sessionData.output?.session_id ||
                sessionData.output?.sessionId;
```

### 2. Fixed User Identification

**Before:**
```typescript
input: {
  user_id: userId  // Generic ID like "user-123"
}
```

**After:**
```typescript
input: {
  user_id: userInfo.email || userId  // Use actual email from IAP headers
}
```

### 3. Updated Function Signatures

Added `userEmail` parameter to `queryAgentWithAPI` function to properly pass email addresses for ADK agents.

### 4. Fixed Shell Script (`test_fixed.sh` - example)

**Before:**
```bash
-d '{
"class_method": "async_stream_query",
"input": {
    "user_id": "${USER_ID}",  # Variables not interpolated in single quotes
    "session_id": "${SESSION_ID}",
    "message": "Hello, what can you help me with?",  # Trailing comma
	}
}'
```

**After:**
```bash
REQUEST_BODY=$(cat <<EOF
{
    "class_method": "async_stream_query",
    "input": {
        "user_id": "$USER_ID",
        "session_id": "$SESSION_ID",
        "message": "Hello, what can you help me with?"
    }
}
EOF
)

curl ... -d "$REQUEST_BODY"
```

## Key Insights

1. **ADK agents require email addresses** as user IDs, not generic identifiers
2. **Session responses vary** in structure - need to check multiple paths
3. **API version matters** - Use `v1beta1` for reasoning engines
4. **IAP headers provide the email** - Use `getUserFromIAPHeaders(request)` to get the actual user email

## Testing the Fix

### Local Testing
```bash
npm run dev
# Visit http://localhost:3000/chat-demo
# Select an ADK agent and test messaging
```

### Production Deployment
```bash
# Build the app
npm run build

# Deploy to Cloud Run
gcloud run deploy YOUR_SERVICE_NAME \
  --source . \
  --region=us-central1 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=sco-agents-np-9orx,GOOGLE_CLOUD_LOCATION=us-central1"
```

### Verify with curl
```bash
# Test creating a session
curl -X POST https://YOUR-SERVICE.run.app/api/agent-engine \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "agentId": "1788443623507886080"
  }'
```

## Files Modified

1. `/web-app/src/app/api/agent-engine/route.ts` - Main agent engine endpoint
2. `/web-app/src/app/api/agent-engine-correct/route.ts` - Alternative implementation
3. `/web-app/src/utils/auth.ts` - Authentication utilities (for Cloud Run ADC)

## Next Steps

1. Monitor Cloud Run logs for any authentication issues
2. Ensure service account has proper IAM roles (`roles/aiplatform.user`)
3. Test with multiple ADK agents to verify consistency
4. Consider implementing session caching for better performance

## Environment Variables Required

```env
GOOGLE_CLOUD_PROJECT=sco-agents-np-9orx
GOOGLE_CLOUD_LOCATION=us-central1
```

## IAM Roles Required for Cloud Run Service Account

```bash
gcloud projects add-iam-policy-binding sco-agents-np-9orx \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@sco-agents-np-9orx.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```