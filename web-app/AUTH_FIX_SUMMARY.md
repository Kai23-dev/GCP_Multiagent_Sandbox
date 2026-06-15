# Authentication Fix Summary

## Issues Fixed

### 1. **Wrong GCP Project Being Used**
**Problem:** ADC was using the user's personal gcloud project instead of the project from environment variables.

**Solution:** Updated `auth.ts` to explicitly set `projectId` from `GOOGLE_CLOUD_PROJECT` env var:
```typescript
export function getGoogleAuthClient(scopes: string[] = DEFAULT_SCOPES): GoogleAuth {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT;
  return new GoogleAuth({
    scopes,
    projectId, // ← Forces use of env var project
  });
}
```

### 2. **Wrong API for Agent Listing**
**Problem:** `/api/agents` was calling Discovery Engine API instead of Vertex AI Reasoning Engines API.

**Solution:** Updated the endpoint to call the correct API:
```typescript
// Before (WRONG - Discovery Engine)
const url = `https://discoveryengine.googleapis.com/v1/projects/${projectId}/locations/${location}/agents`;

// After (CORRECT - Vertex AI Reasoning Engines)
const url = `https://${location}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${location}/reasoningEngines`;
```

## How Authentication Works Now

### Local Development
```
Developer ADC Credentials → Auth with GOOGLE_CLOUD_PROJECT → Vertex AI APIs
     ↓                              ↓                              ↓
(gcloud auth login)        (from .env file)                (correct project)
```

### Production (Cloud Run)
```
IAP User Auth → Service Account (ADC) → Vertex AI APIs
     ↓                 ↓                      ↓
(Google SSO)    (attached to Cloud Run)  (project from env vars)
```

## Key Points

✅ **ADC credentials** authenticate the requests (user in dev, service account in prod)
✅ **GOOGLE_CLOUD_PROJECT** determines which GCP project to target
✅ **IAP headers** provide user identity for audit trails
✅ **Reasoning Engines API** is used for Agent Engine/ADK agents

## Testing Verified

- ✅ Agents are now fetched successfully
- ✅ Correct project is used (`sco-agents-p-t2dp`)
- ✅ ADC provides authentication credentials
- ✅ Environment variables control project targeting

## Files Modified

1. `web-app/src/utils/auth.ts` - Fixed project selection from env vars
2. `web-app/src/app/api/agents/route.ts` - Fixed API endpoint (Discovery Engine → Reasoning Engines)
3. `web-app/AUTHENTICATION.md` - Updated documentation
