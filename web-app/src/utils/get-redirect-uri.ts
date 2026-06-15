import { headers } from 'next/headers';

/**
 * Get the OAuth redirect URI dynamically based on the environment
 * This handles both local development and Cloud Run deployment
 */
export async function getOAuthRedirectUri(): Promise<string> {
  // Check if explicitly set via environment variable
  if (process.env.OAUTH_REDIRECT_URI) {
    return process.env.OAUTH_REDIRECT_URI;
  }

  // Server-side: Use the actual host from request headers
  if (typeof window === 'undefined') {
    try {
      const headersList = await headers();
      const host = headersList.get('host') || headersList.get('x-forwarded-host');

      if (host) {
        // Check if it's already https or needs protocol
        const protocol = headersList.get('x-forwarded-proto') || 'https';
        return `${protocol}://${host}/oauth2callback`;
      }
    } catch (error) {
      console.error('Could not get headers:', error);
    }

    // Fallback for server-side
    return 'http://localhost:3000/oauth2callback';
  }

  // Client-side: Use window.location
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/oauth2callback`;
  }

  // Default fallback
  return 'http://localhost:3000/oauth2callback';
}

/**
 * Get the base URL for the application
 */
export async function getBaseUrl(): Promise<string> {
  // Check if explicitly set via environment variable
  if (process.env.NEXT_PUBLIC_BASE_URL) {
    return process.env.NEXT_PUBLIC_BASE_URL;
  }

  // Server-side
  if (typeof window === 'undefined') {
    try {
      const headersList = await headers();
      const host = headersList.get('host') || headersList.get('x-forwarded-host');

      if (host) {
        const protocol = headersList.get('x-forwarded-proto') || 'https';
        return `${protocol}://${host}`;
      }
    } catch (error) {
      console.error('Could not get headers:', error);
    }

    return 'http://localhost:3000';
  }

  // Client-side
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  return 'http://localhost:3000';
}

/**
 * Get OAuth redirect URI for client-side use (synchronous)
 */
export function getClientOAuthRedirectUri(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/oauth2callback`;
  }
  return 'http://localhost:3000/oauth2callback';
}