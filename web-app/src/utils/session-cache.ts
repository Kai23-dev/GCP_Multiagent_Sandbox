import { unstable_cache } from 'next/cache';

interface CachedSession {
  sessionId: string;
  userId: string;
  agentId: string;
  createdAt: number;
  lastUsed: number;
}

// Cache duration: 24 hours (in seconds)
const CACHE_DURATION = 24 * 60 * 60;

// Session expiry: 2 hours of inactivity (in milliseconds)
const SESSION_EXPIRY = 2 * 60 * 60 * 1000;

/**
 * Get or create a cached session for a user-agent combination
 */
export const getCachedSession = unstable_cache(
  async (userId: string, agentId: string): Promise<string> => {
    const now = Date.now();
    const sessionKey = `${userId}-${agentId}`;
    
    // Try to get existing session from cache
    const existingSession = await getSessionFromCache(sessionKey);
    
    if (existingSession && !isSessionExpired(existingSession, now)) {
      // Update last used timestamp
      await updateSessionLastUsed(sessionKey, now);
      return existingSession.sessionId;
    }
    
    // Create new session
    const newSessionId = generateSessionId(userId, agentId);
    const newSession: CachedSession = {
      sessionId: newSessionId,
      userId,
      agentId,
      createdAt: now,
      lastUsed: now
    };
    
    await storeSessionInCache(sessionKey, newSession);
    return newSessionId;
  },
  ['user-session'],
  {
    revalidate: CACHE_DURATION,
    tags: ['user-sessions']
  }
);

/**
 * Clear all cached sessions for a user
 */
export async function clearUserSessions(): Promise<void> {
  // This will be implemented using Next.js cache tags
  // For now, we'll use a timestamp-based approach
  const { revalidateTag } = await import('next/cache');
  revalidateTag('user-sessions');
}

/**
 * Generate a deterministic session ID for a user-agent combination
 */
function generateSessionId(userId: string, agentId: string): string {
  // Generate a truly persistent session ID based on user and agent only
  // No timestamp to ensure the same user-agent combo always gets the same session ID
  const input = `${userId}-${agentId}`;
  
  // Simple hash function for consistent session IDs
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  // Convert to positive number and create readable session ID
  const positiveHash = Math.abs(hash);
  return `session_${positiveHash.toString(36)}`;
}

/**
 * Check if a session has expired due to inactivity
 */
function isSessionExpired(session: CachedSession, currentTime: number): boolean {
  return (currentTime - session.lastUsed) > SESSION_EXPIRY;
}

// In-memory cache for session data (fallback when Next.js cache is not available)
const sessionCache = new Map<string, CachedSession>();

async function getSessionFromCache(sessionKey: string): Promise<CachedSession | null> {
  // In a real implementation, this would use Next.js cache or Redis
  // For now, using in-memory cache as fallback
  return sessionCache.get(sessionKey) || null;
}

async function storeSessionInCache(sessionKey: string, session: CachedSession): Promise<void> {
  sessionCache.set(sessionKey, session);
}

async function updateSessionLastUsed(sessionKey: string, timestamp: number): Promise<void> {
  const session = sessionCache.get(sessionKey);
  if (session) {
    session.lastUsed = timestamp;
    sessionCache.set(sessionKey, session);
  }
}

/**
 * Get session statistics for debugging
 */
export function getSessionStats(): { totalSessions: number; activeSessions: number } {
  const now = Date.now();
  const sessions = Array.from(sessionCache.values());
  const activeSessions = sessions.filter(session => !isSessionExpired(session, now));
  
  return {
    totalSessions: sessions.length,
    activeSessions: activeSessions.length
  };
}
