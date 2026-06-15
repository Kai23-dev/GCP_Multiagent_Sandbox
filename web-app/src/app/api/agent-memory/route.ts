import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders, getUserFromIAPHeaders } from '@/utils/auth';

interface MemoryContent {
  parts?: Array<{ text?: string }>;
}

interface MemoryItem {
  memory?: MemoryItem;
  content?: MemoryContent | string;
  text?: string;
  summary?: string;
  author?: string;
  title?: string;
  timestamp?: string | number;
}

interface MemoryRequest {
  agentId: string;
  sessionId?: string;
  action?: 'save' | 'search' | 'load';
  query?: string;
  memory?: {
    type: string;
    summary: string;
    timestamp: string;
    messageCount?: number;
  };
}

/**
 * Save session to Agent Engine memory using ADK's async_add_session_to_memory
 */
async function saveSessionToMemory(
  agentId: string,
  sessionId: string,
  userId: string,
  userEmail: string
): Promise<{ success: boolean; error?: string; memoryId?: string }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Get auth headers using service account
    const headers = await getAuthHeaders();

    // Construct the agent resource name
    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;
    const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

    console.log(`Saving session ${sessionId} to memory for user: ${userEmail}`);

    // First, get the session data
    console.log(`Getting session: user_id=${userEmail}, session_id=${sessionId}`);
    
    const getSessionResponse = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_get_session',
        input: {
          user_id: userEmail,
          session_id: sessionId
        }
      }),
    });

    if (!getSessionResponse.ok) {
      const errorText = await getSessionResponse.text();
      console.error('Failed to get session:', errorText);
      throw new Error(`Failed to get session: ${getSessionResponse.status}`);
    }

    const sessionData = await getSessionResponse.json();
    console.log('Retrieved session data:', JSON.stringify(sessionData, null, 2));

    // Now save the session to memory using async_add_session_to_memory
    // ADK expects the session object from the output, not the whole response
    const session = sessionData.output || sessionData;
    console.log('Saving session to memory:', JSON.stringify(session, null, 2));
    
    const saveResponse = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_add_session_to_memory',
        input: {
          session: session
        }
      }),
    });

    if (!saveResponse.ok) {
      const errorText = await saveResponse.text();
      console.error('Failed to save to memory:', errorText);
      throw new Error(`Failed to save to memory: ${saveResponse.status}`);
    }

    const result = await saveResponse.json();
    console.log('✅ Session saved to memory successfully');
    console.log('Memory save result:', JSON.stringify(result, null, 2));

    return {
      success: true,
      memoryId: result.output?.memory_id || result.memory_id || sessionId,
    };

  } catch (error) {
    console.error('Error saving memory to agent:', error);

    // In development, don't fail completely
    if (process.env.NODE_ENV === 'development') {
      console.log('Development mode: Memory logged but not persisted');
      return {
        success: true,
      };
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Load a session (for restoring conversation)
 */
async function loadSession(
  agentId: string,
  sessionId: string,
  userId: string,
  userEmail: string
): Promise<{ success: boolean; session?: MemoryItem; error?: string }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    const headers = await getAuthHeaders();
    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;
    const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

    console.log(`Loading session ${sessionId} for user ${userEmail}`);

    const response = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_get_session',
        input: {
          user_id: userEmail,
          session_id: sessionId
        }
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Failed to load session:', errorText);
      throw new Error(`Failed to load session: ${response.status}`);
    }

    const result = await response.json();
    const session = result.output || result;
    console.log(`✅ Session loaded successfully`);

    return {
      success: true,
      session: session,
    };
  } catch (error) {
    console.error('Error loading session:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Search memories for a user
 */
async function searchMemory(
  agentId: string,
  userId: string,
  userEmail: string,
  query: string
): Promise<{ success: boolean; memories?: MemoryItem[]; error?: string }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    const headers = await getAuthHeaders();
    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;
    const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

    console.log(`Searching memories for user ${userEmail} with query: "${query}"`);

    const response = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_search_memory',
        input: {
          user_id: userEmail,
          query: query
        }
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Failed to search memories:', errorText);
      throw new Error(`Failed to search memories: ${response.status}`);
    }

    const result = await response.json();
    console.log('Search result:', JSON.stringify(result, null, 2));
    
    // Agent Engine returns memories in result.output.memories
    const allMemories = result.output?.memories || result.memories || [];
    console.log(`ADK returned ${allMemories.length} memories for query: "${query}"`);

    // ADK's search might return all memories regardless of query
    // Apply client-side filtering as a fallback
    const filteredMemories = allMemories.filter((memory: MemoryItem) => {
      const memoryData = memory.memory || memory;
      
      // Extract text content from various possible structures
      let textContent = '';
      if (typeof memoryData.content === 'object' && memoryData.content?.parts?.[0]?.text) {
        textContent = memoryData.content.parts[0].text;
      } else if (memoryData.content && typeof memoryData.content === 'string') {
        textContent = memoryData.content;
      } else if (memoryData.text) {
        textContent = memoryData.text;
      } else if (memoryData.summary) {
        textContent = memoryData.summary;
      }
      
      // Case-insensitive search in content
      const queryLower = query.toLowerCase();
      const contentLower = textContent.toLowerCase();
      
      // Check if query appears in content
      return contentLower.includes(queryLower);
    });
    
    console.log(`Filtered to ${filteredMemories.length} memories matching query`);

    return {
      success: true,
      memories: filteredMemories,
    };
  } catch (error) {
    console.error('Error searching memories:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: MemoryRequest = await request.json();
    const { agentId, sessionId, action = 'save', query } = body;

    if (!agentId) {
      return NextResponse.json(
        { error: 'agentId is required' },
        { status: 400 }
      );
    }

    // Get user information from IAP
    const userInfo = getUserFromIAPHeaders(request);

    console.log(`Memory ${action} request from user: ${userInfo.email} (${userInfo.userId})`);
    console.log(`Agent ID: ${agentId}`);

    // Handle different actions
    if (action === 'save') {
      if (!sessionId) {
        return NextResponse.json(
          { error: 'sessionId is required for save action' },
          { status: 400 }
        );
      }

      // Save the current session to memory
      const result = await saveSessionToMemory(
        agentId,
        sessionId,
        userInfo.userId,
        userInfo.email
      );

      if (!result.success) {
        return NextResponse.json(
          { error: result.error || 'Failed to save memory' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        message: 'Session saved to memory successfully',
        memoryId: result.memoryId,
      });
    }

    if (action === 'search') {
      if (!query) {
        return NextResponse.json(
          { error: 'query is required for search action' },
          { status: 400 }
        );
      }

      // Search memories
      const result = await searchMemory(
        agentId,
        userInfo.userId,
        userInfo.email,
        query
      );

      if (!result.success) {
        return NextResponse.json(
          { error: result.error || 'Failed to search memories' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        memories: result.memories,
      });
    }

    if (action === 'load') {
      if (!sessionId) {
        return NextResponse.json(
          { error: 'sessionId is required for load action' },
          { status: 400 }
        );
      }

      // Load session for restoring conversation
      const result = await loadSession(
        agentId,
        sessionId,
        userInfo.userId,
        userInfo.email
      );

      if (!result.success) {
        return NextResponse.json(
          { error: result.error || 'Failed to load session' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        session: result.session,
      });
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}` },
      { status: 400 }
    );

  } catch (error) {
    console.error('Error in agent-memory API:', error);
    return NextResponse.json(
      { error: 'Failed to process memory request', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
