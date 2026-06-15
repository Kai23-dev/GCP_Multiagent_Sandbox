# Simplified Authentication Architecture

## Overview

This web application uses a **simplified authentication approach** that leverages Google Cloud's native authentication mechanisms:

1. **IAP (Identity-Aware Proxy)** - Handles user authentication
2. **ADC (Application Default Credentials)** - Service account calls Google Cloud APIs
3. **Native Google Client Libraries** - No custom OAuth flows

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User's Browser                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ (1) Access Web App
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  IAP (Identity-Aware Proxy)                  │
│  • Authenticates user via Google SSO                         │
│  • Injects user identity into headers                        │
│    - X-Goog-Authenticated-User-Email                         │
│    - X-Goog-Authenticated-User-ID                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ (2) Authenticated Request
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           Cloud Run (Next.js Web Application)                │
│  • Reads user identity from IAP headers                      │
│  • Uses service account with ADC for API calls              │
│  • No client-side OAuth needed                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ (3) API Calls with Service Account
                          ↓
┌─────────────────────────────────────────────────────────────┐
│               Google Cloud APIs                              │
│  • Agent Engine (Vertex AI)                                  │
│  • Dialogflow CX                                             │
│  • Discovery Engine                                          │
│  • Vertex AI (Gemini)                                        │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. User Authentication (IAP)

IAP is enabled on the Cloud Run service and handles all user authentication:

```terraform
resource "google_cloud_run_v2_service" "sco_agents" {
  iap_enabled = true  # IAP handles user authentication
  # ...
}
```

When a user accesses the web app:
- IAP redirects to Google Sign-In if not authenticated
- After authentication, IAP injects user identity headers
- No client-side OAuth flows or token management needed

### 2. User Identity Extraction

Backend APIs extract user information from IAP headers:

```typescript
// utils/auth.ts
export function getUserFromIAPHeaders(request: Request) {
  const iapEmail = request.headers.get('X-Goog-Authenticated-User-Email');
  const iapUserId = request.headers.get('X-Goog-Authenticated-User-ID');
  
  // Returns: { userId, email }
  // Used for logging, session management, and audit trails
}
```

### 3. Service Account API Calls (ADC)

The service account uses ADC to call Google Cloud APIs:

```typescript
// utils/auth.ts
import { GoogleAuth } from 'google-auth-library';

export async function getAccessToken(): Promise<string> {
  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform']
  });
  
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  return token.token;
}
```

ADC automatically discovers credentials from the environment:
- In Cloud Run: Uses the attached service account
- In development: Uses `gcloud auth application-default login`

### 4. API Endpoint Pattern

All API endpoints follow this pattern:

```typescript
export async function POST(request: NextRequest) {
  // 1. Get user identity from IAP headers
  const userInfo = getUserFromIAPHeaders(request);
  console.log(`Request from user: ${userInfo.email}`);
  
  // 2. Get service account credentials using ADC
  const headers = await getAuthHeaders();
  
  // 3. Call Google Cloud API with service account
  const response = await callGoogleCloudAPI(url, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, userInfo.email);  // Pass user email for audit logging
  
  return NextResponse.json(result);
}
```

## IAM Permissions

The web app service account needs these permissions:

```terraform
resource "google_project_iam_member" "web_app" {
  for_each = toset([
    "roles/aiplatform.user",           # Agent Engine & Vertex AI
    "roles/discoveryengine.user",      # Discovery Engine agents
    "roles/dialogflow.client",         # Dialogflow CX agents
  ])
  member = "serviceAccount:${google_service_account.web_app.email}"
}
```

## Benefits of This Approach

### ✅ **Simplified Architecture**
- No custom OAuth flows to maintain
- No token management on the frontend
- No OAuth client secrets to secure

### ✅ **Better Security**
- IAP provides enterprise-grade authentication
- Service account credentials never exposed to client
- Proper separation of user identity and API access

### ✅ **Native Integration**
- Uses Google's recommended authentication patterns
- Leverages ADC for automatic credential discovery
- Works seamlessly with all Google Cloud client libraries

### ✅ **Audit Trail**
- User identity tracked via IAP headers
- All API calls include user context for logging
- Service account actions are auditable

### ✅ **Development Experience**
- Works locally with `gcloud auth application-default login`
- No complex OAuth setup in development
- Consistent auth flow across environments

## Development Setup

### Local Development

1. **Authenticate with gcloud:**
   ```bash
   gcloud auth application-default login
   ```

2. **Configure your environment:**
   ```bash
   cd web-app
   cp .env.example .env
   ```
   
   Edit `.env` and set:
   ```bash
   GOOGLE_CLOUD_PROJECT=sco-agents-p-t2dp  # Or your target project
   GOOGLE_CLOUD_LOCATION=us-central1
   DEV_USER_EMAIL=yourname@example.com      # Optional
   ```

3. **Run the app:**
   ```bash
   npm run dev
   ```

The app will:
- Use ADC credentials from your gcloud login for authentication
- **Use the project from GOOGLE_CLOUD_PROJECT env var** (not from ADC)
- Use `DEV_USER_EMAIL` (or default) as the simulated user identity
- Function identically to production, just without IAP

**Important:** The `GOOGLE_CLOUD_PROJECT` environment variable determines which GCP project the API calls target, regardless of what project your gcloud ADC is configured for. This ensures you can develop against the correct project even if your default gcloud project is different.

### Production Deployment

No special setup needed! The deployment pipeline:

1. Builds Docker image from `web-app/Dockerfile`
2. Pushes to Artifact Registry
3. Terraform deploys to Cloud Run with:
   - IAP enabled
   - Service account attached
   - Proper IAM permissions configured

## API Examples

### Fetching Agents

```typescript
// Frontend (no auth needed)
const response = await fetch('/api/agents');
const data = await response.json();

// Backend automatically:
// 1. Gets user from IAP headers
// 2. Uses service account to call Discovery Engine API
// 3. Returns agents list
```

### Chatting with Agent Engine

```typescript
// Frontend (no auth needed)
const response = await fetch('/api/agent-engine', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Hello',
    agentId: 'my-agent-id',
  }),
});

// Backend automatically:
// 1. Gets user identity for session management
// 2. Uses service account to call Agent Engine API
// 3. Passes user context for audit logging
```

### Vertex AI (Gemini)

```typescript
// Frontend (no auth needed)
const response = await fetch('/api/vertex-ai', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'Explain quantum computing',
  }),
});

// Backend automatically:
// 1. Gets user from IAP
// 2. Uses service account for Vertex AI API
// 3. Logs request with user context
```

## Troubleshooting

### "Permission denied" errors

Check that the service account has the required IAM roles:
```bash
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:web-app@*"
```

### Local development not working

Ensure ADC is configured:
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### IAP not working

Verify IAP is enabled and configured:
```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=sco-agents-SERVICE_ID
```

## Migration Notes

### What Was Removed

The following complexity was removed:

- ❌ Custom OAuth2 flows in the frontend
- ❌ Token management in localStorage
- ❌ OAuth client ID/secret environment variables
- ❌ Custom token refresh logic
- ❌ Google Identity Services (GIS) integration
- ❌ User token passing to backend APIs

### What Replaced It

- ✅ IAP for user authentication (already configured)
- ✅ ADC for service account credentials (native)
- ✅ IAP headers for user identity (automatic)
- ✅ Native Google client libraries (standard)

### Breaking Changes

**None for end users!** The authentication is handled transparently by IAP.

For developers:
- Remove any OAuth client configuration
- Use `gcloud auth application-default login` for local development
- Backend APIs now use service account credentials exclusively

## References

- [Identity-Aware Proxy Documentation](https://cloud.google.com/iap/docs)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Google Auth Library for Node.js](https://github.com/googleapis/google-auth-library-nodejs)
- [Cloud Run Authentication](https://cloud.google.com/run/docs/authenticating/overview)
