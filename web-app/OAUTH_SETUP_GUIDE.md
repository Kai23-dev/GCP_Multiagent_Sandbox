# OAuth Setup Guide for Local Development and Cloud Run Deployment

## Configure OAuth 2.0 in Google Cloud Console

1. **Go to the Google Cloud Console**
   - Navigate to: https://console.cloud.google.com
   - Select your project: `sco-agents-np-64g9`

2. **Navigate to OAuth Consent Screen**
   - Go to "APIs & Services" → "OAuth consent screen"
   - Ensure your app is configured (can be "Internal" for organization users or "External" for testing)

3. **Configure OAuth 2.0 Client ID**
   - Go to "APIs & Services" → "Credentials"
   - Find your OAuth 2.0 Client ID: `6885718459-3q28c7f872rol3tqt8h50k6pl6t716b0.apps.googleusercontent.com`
   - Click on it to edit

4. **Add Authorized JavaScript Origins**
   Add ALL of these origins to support different local development scenarios:
   ```
   http://localhost
   http://localhost:3000
   http://localhost:3001
   http://localhost:3002
   http://localhost:3003
   http://127.0.0.1
   http://127.0.0.1:3000
   http://127.0.0.1:3001
   http://127.0.0.1:3002
   http://127.0.0.1:3003
   ```

5. **Add Authorized Redirect URIs** (if using authorization code flow)
   ```
   http://localhost:3000/api/auth/callback/google
   http://localhost:3001/api/auth/callback/google
   http://localhost:3002/api/auth/callback/google
   http://localhost:3003/api/auth/callback/google
   ```

6. **Save Changes**
   - Click "SAVE" at the bottom of the page
   - Changes may take a few minutes to propagate

## Test the Configuration

1. **Restart your development server**
   ```bash
   npm run dev
   ```

2. **Clear browser cache and cookies**
   - Open Chrome DevTools (F12)
   - Go to Application → Storage
   - Click "Clear site data"

3. **Test OAuth Sign-In**
   - Navigate to http://localhost:3002 (or whatever port your server is using)
   - Click "Sign in with Google"
   - You should see the Google OAuth consent screen
   - After authorization, you should be redirected back to your app

## Troubleshooting

### Error: "You can't sign in to this app because it doesn't comply with Google's OAuth 2.0 policy"
- **Cause**: The origin (localhost:port) is not in the authorized JavaScript origins list
- **Solution**: Add the specific localhost:port combination to the OAuth client configuration

### Error: "invalid_grant" or "invalid_rapt"
- **Cause**: Token has expired or requires re-authentication
- **Solution**: Clear localStorage and sign in again with `prompt: 'consent'`

### Port Conflicts
- If port 3000 is in use, the dev server will automatically use 3001, 3002, etc.
- Make sure all potential ports are added to the OAuth configuration

## Current OAuth Client Configuration

- **Client ID**: `6885718459-3q28c7f872rol3tqt8h50k6pl6t716b0.apps.googleusercontent.com`
- **Project**: `sco-agents-np-64g9`
- **Scopes Required**:
  - `https://www.googleapis.com/auth/cloud-platform`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`

## Notes

- The OAuth client configuration is managed in the Google Cloud Console, not in your code
- Changes to OAuth configuration can take 5-10 minutes to propagate
- For production deployment, you'll need to add your production domain to the authorized origins

## Cloud Run Deployment

### Key Issues and Solutions

#### 1. OAuth Configuration in Cloud Run
**How it works**: The app fetches OAuth configuration at runtime via the `/api/config` endpoint, which reads from server environment variables set by Terraform.

**No build-time configuration needed** - GitLab CI builds the image normally, and Terraform sets the OAuth variables at deployment:
```hcl
# In web-app.tf - automatically set by Terraform
env {
  name  = "OAUTH_CLIENT_ID"
  value = var.oauth_client_id
}
env {
  name  = "OAUTH_CLIENT_SECRET"
  value = var.oauth_client_secret
}
```

The client fetches this configuration dynamically:
```javascript
// Handled automatically by useConfig() hook
fetch('/api/config') // Returns OAuth settings from server env vars
```

#### 2. OAuth Users Can't Access Agents
**Problem**: Users authenticating via OAuth don't have IAM permissions to list or query agents.

**Solution**: Grant appropriate IAM roles in Terraform:
```hcl
# In iam.tf - grants access to all users in your domain
resource "google_project_iam_member" "oauth_users_discovery_engine" {
  project = google_project.agent_project.project_id
  role    = "roles/discoveryengine.viewer"
  member  = "domain:davita.com"
}

resource "google_project_iam_member" "oauth_users_vertex_ai" {
  project = google_project.agent_project.project_id
  role    = "roles/aiplatform.user"
  member  = "domain:davita.com"
}
```

#### 3. Add Cloud Run URL to OAuth Configuration
Once deployed, add your Cloud Run URL to the OAuth client:

**Authorized JavaScript Origins**:
```
https://sco-agents-{env}-{project-id}.a.run.app
```

**Authorized Redirect URIs**:
```
https://sco-agents-{env}-{project-id}.a.run.app/oauth2callback
```

### Deployment Steps

1. **Set Terraform variables** in your `.tfvars` file:
   ```hcl
   oauth_client_id     = "your-client-id.apps.googleusercontent.com"
   oauth_client_secret = "your-client-secret"
   ```

2. **Deploy with Terraform** (image is built by GitLab CI):
   ```bash
   terraform apply
   ```

3. **Update OAuth client in Google Console** with the Cloud Run URL

4. **Test the deployment**:
   ```bash
   # Check configuration
   curl https://your-app.run.app/api/config

   # Check logs
   gcloud run logs read --project your-project
   ```

### Runtime Configuration Fallback

The app also provides runtime configuration via `/api/config` endpoint as a fallback:
```javascript
// Automatically used by useConfig() hook
fetch('/api/config')
  .then(res => res.json())
  .then(config => {
    // Uses OAuth client ID from server environment
  });
```