import { GoogleAuth } from "google-auth-library";

let authClient: GoogleAuth | null = null;

export function getAuth(): GoogleAuth {
  if (!authClient) {
    authClient = new GoogleAuth({
      scopes: [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/trace.readonly",
        "https://www.googleapis.com/auth/logging.read",
      ],
    });
  }
  return authClient;
}

export async function getAccessToken(): Promise<string> {
  const auth = getAuth();
  const client = await auth.getClient();
  const tokenResponse = await client.getAccessToken();
  return tokenResponse.token || "";
}

export function getProjectId(): string {
  return process.env.GOOGLE_CLOUD_PROJECT || process.env.GCP_PROJECT_ID || "";
}
