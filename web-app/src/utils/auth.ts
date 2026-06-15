/**
 * Simplified Authentication for Cloud Run with IAP
 * 
 * This module provides a clean authentication strategy:
 * 1. IAP provides user identity (email) via headers
 * 2. Service account uses ADC (Application Default Credentials) to make API calls
 * 3. User context is passed through headers for audit/logging
 * 
 * No complex OAuth flows needed - IAP handles user authentication,
 * and the service account has necessary GCP permissions.
 */

import { GoogleAuth } from 'google-auth-library';

// Scopes needed for GCP services
const DEFAULT_SCOPES = [
  'https://www.googleapis.com/auth/cloud-platform',
];

/**
 * Get an authenticated GoogleAuth client using ADC
 * This automatically picks up credentials from the environment
 * BUT uses the project from GOOGLE_CLOUD_PROJECT env var, not from ADC
 */
export function getGoogleAuthClient(scopes: string[] = DEFAULT_SCOPES): GoogleAuth {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT;
  
  if (!projectId) {
    console.warn('⚠️  GOOGLE_CLOUD_PROJECT not set - ADC will use default project from credentials');
  } else {
    console.log(`🔧 Using project from env: ${projectId}`);
  }
  
  return new GoogleAuth({
    scopes,
    projectId, // Use project from env vars, not from ADC
    // This ensures API calls go to the correct project
  });
}

/**
 * Get access token for Google Cloud APIs using ADC
 * Sets quota project to ensure billing is correct
 */
export async function getAccessToken(): Promise<string> {
  const auth = getGoogleAuthClient();
  const client = await auth.getClient();
  
  // Set quota project for billing
  const projectId = process.env.GOOGLE_CLOUD_PROJECT;
  if (projectId) {
    (client as unknown as { quotaProjectId: string }).quotaProjectId = projectId;
    // Also set these environment variables to suppress warnings
    process.env.GOOGLE_CLOUD_QUOTA_PROJECT = projectId;
    process.env.GCLOUD_PROJECT = projectId;
  }
  
  const token = await client.getAccessToken();
  
  if (!token.token) {
    throw new Error('Failed to obtain access token from ADC');
  }
  
  return token.token;
}

/**
 * Get authorization headers with access token
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

/**
 * Extract user identity from IAP headers
 * Works in production (IAP) and development (fallback)
 */
export function getUserFromIAPHeaders(request: Request): { userId: string; email: string } {
  // Production: Get user from IAP headers
  const iapEmail = request.headers.get('X-Goog-Authenticated-User-Email') ||
                   request.headers.get('x-goog-authenticated-user-email');
  const iapUserId = request.headers.get('X-Goog-Authenticated-User-ID') ||
                    request.headers.get('x-goog-authenticated-user-id');

  if (iapEmail) {
    // Remove IAP prefix from email
    const cleanEmail = iapEmail.replace(/^accounts\.google\.com:/, '');
    const userId = iapUserId || cleanEmail.split('@')[0] || 'unknown';
    
    console.log(`IAP User: ${cleanEmail} (${userId})`);
    return { userId, email: cleanEmail };
  }

  // Development: Use environment variable or default
  const devEmail = process.env.DEV_USER_EMAIL || 'developer@example.com';
  const devUserId = devEmail.split('@')[0].replace(/[^a-zA-Z0-9]/g, '_');
  
  console.log(`Development User: ${devEmail} (${devUserId})`);
  return { userId: devUserId, email: devEmail };
}

/**
 * Make authenticated request to Google Cloud APIs
 * Uses service account credentials with user context for audit trails
 */
export async function callGoogleCloudAPI(
  url: string,
  options: RequestInit = {},
  userEmail?: string
): Promise<Response> {
  const headers = await getAuthHeaders();
  
  // Add user context for audit logging
  if (userEmail) {
    headers['X-Goog-User-Email'] = userEmail;
  }
  
  console.log(`API Call: ${options.method || 'GET'} ${url}${userEmail ? ` (user: ${userEmail})` : ''}`);
  
  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });
}

/**
 * Get ID token for service-to-service calls
 * Used for calling other Cloud Run services
 */
export async function getIdToken(targetAudience: string): Promise<string> {
  const auth = getGoogleAuthClient();
  const client = await auth.getIdTokenClient(targetAudience);
  const token = await client.idTokenProvider.fetchIdToken(targetAudience);
  return token;
}

/**
 * Make authenticated service-to-service call
 * Used for calling other Cloud Run services
 */
export async function callCloudRunService(
  url: string,
  options: RequestInit = {},
  userEmail?: string
): Promise<Response> {
  const targetAudience = new URL(url).origin;
  const idToken = await getIdToken(targetAudience);
  
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${idToken}`,
    'Content-Type': 'application/json',
  };
  
  // Add user context
  if (userEmail) {
    headers['X-Goog-User-Email'] = userEmail;
  }
  
  console.log(`Service Call: ${options.method || 'GET'} ${url}${userEmail ? ` (user: ${userEmail})` : ''}`);
  
  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });
}
