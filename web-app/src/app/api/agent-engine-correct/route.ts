import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders, getUserFromIAPHeaders } from '@/utils/auth';
import { getCachedSession, clearUserSessions } from '@/utils/session-cache';

interface AgentEngineRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  userAccessToken?: string;
  clearSession?: boolean;
}

/**
 * Query Agent Engine using the correct format from ADK documentation
 * Based on: https://google.github.io/adk-docs/deploy/agent-engine/
 */
export async function POST(request: NextRequest) {
  try {
    const body: AgentEngineRequest = await request.json();
    const { message, agentId, sessionId: providedSessionId, userAccessToken, clearSession } = body;

    if (!message || !agentId) {
      return NextResponse.json(
        { error: 'Message and agentId are required' },
        { status: 400 }
      );
    }

    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Get user information
    const userInfo = getUserFromIAPHeaders(request);
    const userId = userInfo.userId || `user-${Date.now()}`;

    // Get auth headers
    const headers = userAccessToken
      ? {
          'Authorization': `Bearer ${userAccessToken}`,
          'Content-Type': 'application/json',
        }
      : await getAuthHeaders();

    // Construct the agent resource name
    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;

    // Check if we have a cached session or use the provided one
    let sessionId = providedSessionId;

    if (clearSession && userId) {
      await clearUserSessions();
      sessionId = undefined;
    }

    if (!sessionId) {
      // Try to get cached session
      const cachedSession = await getCachedSession(userId, agentId);
      if (cachedSession) {
        sessionId = cachedSession;
        console.log(`Using cached session: ${sessionId}`);
      }
    }

    // If we don't have a session, create one first
    if (!sessionId) {
      console.log('Creating new session for user:', userId);

      const createSessionUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

      const createSessionResponse = await fetch(createSessionUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          class_method: 'async_create_session',
          input: {
            user_id: userInfo.email || userId  // Use email for ADK agents
          }
        }),
      });

      if (createSessionResponse.ok) {
        const sessionData = await createSessionResponse.json();
        console.log('Session created:', JSON.stringify(sessionData));

        // Parse session ID from various possible locations
        // The output might be a JSON string or an object
        let sessionOutput = sessionData.output;

        if (typeof sessionOutput === 'string') {
          try {
            sessionOutput = JSON.parse(sessionOutput);
          } catch {
            // If it's not JSON, use as is
          }
        }

        // Try different possible paths for session ID
        sessionId = sessionOutput?.id ||
                   sessionOutput?.session_id ||
                   sessionOutput?.sessionId ||
                   sessionData.output?.id ||
                   sessionData.output?.session_id ||
                   sessionData.output?.sessionId ||
                   sessionData.session_id ||
                   sessionData.id;

        if (!sessionId) {
          // Generate a session ID if not returned
          sessionId = `session-${userId}-${Date.now()}`;
        }

        console.log(`New session created: ${sessionId}`);
      } else {
        // If session creation fails, generate a fallback session ID
        console.warn('Session creation failed, using generated ID');
        sessionId = `session-${userId}-${Date.now()}`;
      }
    }

    // Now send the actual query using streamQuery with SSE
    const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:streamQuery?alt=sse`;

    console.log(`Sending query to: ${queryUrl}`);
    console.log(`Session ID: ${sessionId}`);
    console.log(`Message: ${message}`);

    const queryResponse = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        class_method: 'async_stream_query',
        input: {
          user_id: userInfo.email || userId,  // Use email for ADK agents
          session_id: sessionId,
          message: message
        }
      }),
    });

    if (!queryResponse.ok) {
      const errorText = await queryResponse.text();
      console.error('Query failed:', errorText);

      // Try without SSE parameter
      const regularQueryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:streamQuery`;

      const regularQueryResponse = await fetch(regularQueryUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          class_method: 'async_stream_query',
          input: {
            user_id: userInfo.email || userId,  // Use email for ADK agents
            session_id: sessionId,
            message: message
          }
        }),
      });

      if (!regularQueryResponse.ok) {
        // Try the standard query endpoint with class_method
        const standardQueryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

        const standardQueryResponse = await fetch(standardQueryUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            class_method: 'stream_query',  // Try non-async version
            input: {
              user_id: userInfo.email || userId,  // Use email for ADK agents
              session_id: sessionId,
              message: message
            }
          }),
        });

        if (!standardQueryResponse.ok) {
          const standardError = await standardQueryResponse.text();
          throw new Error(`All query methods failed. Last error: ${standardError.substring(0, 200)}`);
        }

        // Process standard query response
        const standardData = await standardQueryResponse.json();
        const responseText = extractResponseText(standardData);

        return NextResponse.json({
          response: responseText,
          sessionId: sessionId,
          success: true,
        });
      }

      // Process regular query response
      const regularData = await regularQueryResponse.text();
      const responseText = processStreamResponse(regularData);

      return NextResponse.json({
        response: responseText,
        sessionId: sessionId,
        success: true,
      });
    }

    // Process SSE response
    const responseText = await queryResponse.text();
    console.log('Raw SSE response:', responseText.substring(0, 500));

    // Parse SSE format
    const parsedResponse = processSSEResponse(responseText);

    return NextResponse.json({
      response: parsedResponse,
      sessionId: sessionId,
      success: true,
    });

  } catch (error) {
    console.error('Error in agent-engine-correct API:', error);
    return NextResponse.json(
      {
        error: 'Failed to query agent',
        details: error instanceof Error ? error.message : 'Unknown error',
        success: false
      },
      { status: 500 }
    );
  }
}

function processSSEResponse(sseText: string): string {
  // Parse Server-Sent Events format
  const lines = sseText.split('\n');
  let fullResponse = '';

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const dataStr = line.substring(6);
      if (dataStr && dataStr !== '[DONE]') {
        try {
          const data = JSON.parse(dataStr);
          const text = extractResponseText(data);
          if (text) {
            fullResponse += text;
          }
        } catch {
          // Not JSON, might be plain text
          fullResponse += dataStr;
        }
      }
    }
  }

  return fullResponse || 'No response received';
}

function processStreamResponse(streamText: string): string {
  // Try to parse as JSON first
  try {
    const data = JSON.parse(streamText);
    return extractResponseText(data);
  } catch {
    // Not JSON, return as is
    return streamText || 'No response received';
  }
}

function extractResponseText(data: unknown): string {
  // Type guard for safe property access
  if (!data || typeof data !== 'object') {
    return typeof data === 'string' ? data : JSON.stringify(data);
  }

  const obj = data as Record<string, unknown>;

  // Try various response formats
  const output = obj.output as Record<string, unknown> | string | undefined;

  if (output && typeof output === 'object') {
    if (typeof output.text === 'string') return output.text;
    if (typeof output.response === 'string') return output.response;
    if (typeof output.message === 'string') return output.message;
    return JSON.stringify(output);
  }

  if (typeof output === 'string') {
    return output;
  }

  if (typeof obj.text === 'string') {
    return obj.text;
  }
  if (typeof obj.response === 'string') {
    return obj.response;
  }
  if (typeof obj.message === 'string') {
    return obj.message;
  }

  return JSON.stringify(data);
}