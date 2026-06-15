# Cloud Run Deployment Guide for ADK Agent Web App

## Prerequisites

1. Google Cloud Project with the following APIs enabled:
   - Cloud Run API
   - Vertex AI API
   - IAP (Identity-Aware Proxy) API
   - Artifact Registry API

2. Service Account with proper permissions (see below)

3. ADK Agents deployed to Agent Engine

## Service Account Permissions Required

The Cloud Run service account needs the following IAM roles:

```bash
# Required roles for the service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# For accessing reasoning engines
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.admin"

# For logging
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

## Environment Variables

Create a `.env` file or set these in Cloud Run:

```env
GOOGLE_CLOUD_PROJECT=sco-agents-np-9orx
GOOGLE_CLOUD_LOCATION=us-central1
```

## Building and Deploying

### 1. Build the Docker Image

```bash
cd web-app

# Build locally
docker build -t gcr.io/YOUR_PROJECT_ID/adk-agent-web-app .

# Or use Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/adk-agent-web-app
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy adk-agent-web-app \
  --image gcr.io/YOUR_PROJECT_ID/adk-agent-web-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1 \
  --service-account YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Enable IAP (Optional but Recommended)

To enable Identity-Aware Proxy for authentication:

```bash
# Create backend service
gcloud compute backend-services create adk-agent-backend \
  --global \
  --load-balancing-scheme=EXTERNAL \
  --protocol=HTTP

# Configure IAP
gcloud iap web enable \
  --resource-type=backend-services \
  --service=adk-agent-backend
```

## Known Issues and Solutions

### Issue 1: ADK Agent Methods Not Found

**Error**: `Agent Engine Error: Default method 'query' not found` or `User-specified method 'async_stream_query' not found`

**Solution**: Ensure the ADK agent ID is included in the detection list in the API routes:
- `/api/agent-engine/route.ts`
- `/api/agent-engine-stream/route.ts`

Add your agent ID to the array:
```typescript
const isADKAgent = agentData.spec?.agentFramework === 'google-adk' ||
  ['607906784857817088', '5846085732698947584', '2701781544422342656', 'YOUR_AGENT_ID'].includes(agentId);
```

### Issue 2: Authentication Errors

**Error**: `401 Unauthorized` or `403 Forbidden`

**Solution**:
1. Verify the service account has the correct permissions
2. Check that Application Default Credentials are properly configured
3. For local development, run: `gcloud auth application-default login`

### Issue 3: Session Management

ADK agents require proper session management:
1. Create session with `async_create_session`
2. Use the returned session ID for all subsequent queries
3. Pass user email (from IAP headers in production) as user_id

## Testing

### Local Testing
```bash
cd web-app
npm run dev

# Test with curl
curl -X POST http://localhost:3000/api/agent-engine \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "agentId": "YOUR_AGENT_ID"
  }'
```

### Production Testing
```bash
# Get the Cloud Run URL
SERVICE_URL=$(gcloud run services describe adk-agent-web-app --region us-central1 --format 'value(status.url)')

# Test the endpoint
curl -X POST $SERVICE_URL/api/agent-engine \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "message": "Hello",
    "agentId": "YOUR_AGENT_ID"
  }'
```

## Monitoring and Debugging

### View Cloud Run Logs
```bash
gcloud run services logs read adk-agent-web-app --region us-central1
```

### View Agent Engine Logs
```bash
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine AND resource.labels.reasoning_engine_id=YOUR_AGENT_ID" --limit 50
```

## ADK Agent Configuration

ADK agents must support the following methods:
- `async_create_session` - Create a new session
- `async_stream_query` - Query with streaming response
- `async_get_session` - Get session details
- `async_list_sessions` - List all sessions

Example ADK agent implementation should handle these methods properly.

## Security Best Practices

1. **Always use IAP in production** to authenticate users
2. **Never expose service account keys** - use Workload Identity or default service accounts
3. **Implement rate limiting** to prevent abuse
4. **Log all API calls** for audit purposes
5. **Use secrets manager** for sensitive configuration

## Troubleshooting Checklist

- [ ] Service account has `roles/aiplatform.user` role
- [ ] APIs are enabled (Vertex AI, Cloud Run, IAP)
- [ ] Environment variables are set correctly
- [ ] ADK agent ID is in the detection list
- [ ] Application Default Credentials are configured
- [ ] Cloud Run service is deployed in the same region as agents
- [ ] IAP is configured (if using authentication)