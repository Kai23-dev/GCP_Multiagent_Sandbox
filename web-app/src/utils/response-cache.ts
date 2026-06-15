/**
 * Response caching utility for agent responses
 * Implements LRU cache with TTL for better performance
 */

interface CacheEntry {
  response: string;
  timestamp: number;
  hits: number;
}

class ResponseCache {
  private cache: Map<string, CacheEntry>;
  private maxSize: number;
  private ttl: number; // Time to live in milliseconds

  constructor(maxSize = 100, ttl = 5 * 60 * 1000) { // Default 5 minutes TTL
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  /**
   * Generate cache key from request parameters
   */
  private generateKey(agentId: string, message: string, userId?: string): string {
    const normalizedMessage = message.toLowerCase().trim();
    return `${agentId}:${userId || 'anonymous'}:${normalizedMessage}`;
  }

  /**
   * Get cached response if available and not expired
   */
  get(agentId: string, message: string, userId?: string): string | null {
    const key = this.generateKey(agentId, message, userId);
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // Check if cache entry has expired
    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    // Update hit count and move to end (LRU)
    entry.hits++;
    this.cache.delete(key);
    this.cache.set(key, entry);

    console.log(`Cache hit for key: ${key} (hits: ${entry.hits})`);
    return entry.response;
  }

  /**
   * Store response in cache
   */
  set(agentId: string, message: string, response: string, userId?: string): void {
    const key = this.generateKey(agentId, message, userId);

    // Implement LRU eviction if cache is full
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
        console.log(`Evicted cache entry: ${firstKey}`);
      }
    }

    this.cache.set(key, {
      response,
      timestamp: Date.now(),
      hits: 0,
    });

    console.log(`Cached response for key: ${key}`);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    console.log('Response cache cleared');
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number;
    maxSize: number;
    hitRate: number;
    topEntries: Array<{ key: string; hits: number }>;
  } {
    let totalHits = 0;
    const entries: Array<{ key: string; hits: number }> = [];

    this.cache.forEach((entry, key) => {
      totalHits += entry.hits;
      entries.push({ key, hits: entry.hits });
    });

    // Sort by hits descending
    entries.sort((a, b) => b.hits - a.hits);

    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hitRate: this.cache.size > 0 ? totalHits / this.cache.size : 0,
      topEntries: entries.slice(0, 5),
    };
  }

  /**
   * Preload cache with common queries
   */
  preload(entries: Array<{ agentId: string; message: string; response: string; userId?: string }>): void {
    entries.forEach(({ agentId, message, response, userId }) => {
      this.set(agentId, message, response, userId);
    });
    console.log(`Preloaded ${entries.length} cache entries`);
  }
}

// Singleton instance
let cacheInstance: ResponseCache | null = null;

/**
 * Get or create cache instance
 */
export function getResponseCache(): ResponseCache {
  if (!cacheInstance) {
    cacheInstance = new ResponseCache();

    // Preload with common queries for better UX
    cacheInstance.preload([
      {
        agentId: '*',
        message: 'hello',
        response: "Hello! I'm your AI assistant. How can I help you today? Feel free to ask me anything!",
      },
      {
        agentId: '*',
        message: 'hi',
        response: "Hi there! I'm ready to assist you. What would you like to know or discuss?",
      },
      {
        agentId: '*',
        message: 'what can you do',
        response: "I can help you with a variety of tasks including:\n\n• Answering questions on various topics\n• Providing explanations and tutorials\n• Helping with problem-solving\n• Offering creative suggestions\n• Assisting with analysis and research\n\nWhat would you like to explore?",
      },
      {
        agentId: '*',
        message: 'help',
        response: "I'm here to help! You can ask me questions, request explanations, seek advice, or explore ideas together. Just type your question or topic of interest, and I'll do my best to assist you.",
      },
    ]);
  }

  return cacheInstance;
}

/**
 * Clear the cache instance
 */
export function clearResponseCache(): void {
  if (cacheInstance) {
    cacheInstance.clear();
  }
}

/**
 * Get cache statistics
 */
export function getCacheStats() {
  if (cacheInstance) {
    return cacheInstance.getStats();
  }
  return null;
}