import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders, getUserFromIAPHeaders } from '@/utils/auth';
import { getCachedSession } from '@/utils/session-cache';

interface StreamRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  userAccessToken?: string;
}

// Response streaming helper
function createStreamResponse(stream: ReadableStream) {
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

/**
 * Stream agent response - simplified version for ADK agents
 */
async function* streamAgentQuery(
  message: string,
  agentId: string,
  userId: string,
  sessionId?: string,
  userAccessToken?: string,
  userEmail?: string
): AsyncGenerator<string> {
  let finalSessionId = sessionId; // Track session ID throughout the stream
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Get auth headers
    const headers = userAccessToken
      ? {
          'Authorization': `Bearer ${userAccessToken}`,
          'Content-Type': 'application/json',
        }
      : await getAuthHeaders();

    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;

    // Check if this is an ADK agent
    const agentUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}`;
    const agentCheckResponse = await fetch(agentUrl, { headers });

    if (!agentCheckResponse.ok) {
      throw new Error(`Failed to get agent details: ${agentCheckResponse.status}`);
    }

    const agentData = await agentCheckResponse.json();
    const isADKAgent = agentData.spec?.agentFramework === 'google-adk' ||
                       ['607906784857817088', '5846085732698947584', '2701781544422342656', '1788443623507886080'].includes(agentId);

    console.log('Agent framework:', agentData.spec?.agentFramework);

    yield `data: {"type": "start", "message": "Connecting to agent..."}\n\n`;

    if (isADKAgent) {
      console.log('ADK agent detected - using proper session flow');

      // Step 1: Create or use existing session
      let sessionIdToUse = sessionId;

      // Create a new session if we don't have one or if it's not a valid ADK session ID
      // Valid ADK session IDs are numeric strings
      const isValidADKSession = sessionIdToUse && /^\d+$/.test(sessionIdToUse);
      if (!isValidADKSession) {
        // Create a new session using async_create_session
        console.log('Creating new ADK session...');
        const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

        const createSessionResponse = await fetch(queryUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            class_method: 'async_create_session',
            input: {
              user_id: userEmail || userId  // Use email for ADK agents
            }
          })
        });

        if (createSessionResponse.ok) {
          const sessionData = await createSessionResponse.json();
          console.log('Session creation response:', JSON.stringify(sessionData));

          // Parse session ID from various possible locations
          let sessionOutput = sessionData.output;
          if (typeof sessionOutput === 'string') {
            try {
              sessionOutput = JSON.parse(sessionOutput);
            } catch {
              // If it's not JSON, use as is
            }
          }

          sessionIdToUse = sessionOutput?.id ||
                         sessionOutput?.session_id ||
                         sessionOutput?.sessionId ||
                         sessionData.output?.id ||
                         sessionData.output?.session_id ||
                         sessionData.output?.sessionId;

          finalSessionId = sessionIdToUse; // Update final session ID
          console.log('Created ADK session:', sessionIdToUse);
          yield `data: {"type": "info", "message": "Session created: ${sessionIdToUse}"}\n\n`;
        } else {
          const error = await createSessionResponse.text();
          console.error('Failed to create session:', error);
          yield `data: {"type": "error", "message": "Failed to create session"}\n\n`;
          return;
        }
      }

      // Step 2: Query with async_stream_query using the session
      const streamQueryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:streamQuery?alt=sse`;

      console.log('Sending message to ADK agent with session:', sessionIdToUse);
      const streamResponse = await fetch(streamQueryUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          class_method: 'async_stream_query',
          input: {
            user_id: userEmail || userId,  // Use email for ADK agents
            session_id: sessionIdToUse,
            message: message
          }
        })
      });

      if (streamResponse.ok) {
        const responseText = await streamResponse.text();
        console.log('ADK stream response received, length:', responseText.length);

        // Try parsing as JSON first (ADK agents return plain JSON)
        try {
          const data = JSON.parse(responseText);

          // Extract text from the ADK agent response format
          if (data.content?.parts?.[0]?.text) {
            const text = data.content.parts[0].text;
            yield `data: {"type": "chunk", "content": "${text.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
          } else if (data.text) {
            yield `data: {"type": "chunk", "content": "${data.text.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
          } else if (data.message) {
            yield `data: {"type": "chunk", "content": "${data.message.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
          } else {
            // Send raw response if no text field found
            yield `data: {"type": "chunk", "content": "${JSON.stringify(data).replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
          }
        } catch {
          // Not JSON, check if it's SSE format
          if (responseText.includes('data:')) {
            const lines = responseText.split('\n');
            for (const line of lines) {
              if (line.startsWith('data:')) {
                const jsonStr = line.substring(5).trim();
                if (jsonStr && jsonStr !== '[DONE]') {
                  try {
                    const data = JSON.parse(jsonStr);
                    // Extract text from various possible formats
                    let text = '';
                    if (data.content?.parts?.[0]?.text) {
                      text = data.content.parts[0].text;
                    } else if (data.text) {
                      text = data.text;
                    } else if (data.message) {
                      text = data.message;
                    }

                    if (text) {
                      yield `data: {"type": "chunk", "content": "${text.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
                    }
                  } catch (parseError) {
                    console.error('Failed to parse SSE data:', parseError);
                  }
                }
              }
            }
          } else if (responseText) {
            // Not SSE or JSON format, send as single chunk
            yield `data: {"type": "chunk", "content": "${responseText.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
          }
        }

        yield `data: {"type": "end", "message": "Complete", "sessionId": "${finalSessionId}"}\n\n`;
        return;
      } else {
        const error = await streamResponse.text();
        console.error('ADK stream query failed:', error);
        yield `data: {"type": "error", "message": "Failed to query ADK agent"}\n\n`;
        return;
      }
    }


    // Non-ADK agent handling
    const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

    // Try with input struct format
    let response = await fetch(queryUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        input: {
          query: message
        }
      }),
    });

    // Fallback to simple query format if struct format fails
    if (!response.ok) {
      console.log('Trying simple query format for non-ADK agent');
      response = await fetch(queryUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: message
        }),
      });
    }

    if (!response.ok) {
      // Try using Gemini as fallback
      console.log('Agent query failed, falling back to Gemini');

      yield `data: {"type": "info", "message": "Using Gemini AI..."}\n\n`;

      const geminiUrl = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/gemini-1.5-flash:generateContent`;

      const geminiResponse = await fetch(geminiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          contents: [
            {
              role: 'user',
              parts: [{ text: message }]
            }
          ],
          generationConfig: {
            temperature: 0.7,
            topP: 0.95,
            topK: 40,
            maxOutputTokens: 1024,
          }
        }),
      });

      if (!geminiResponse.ok) {
        throw new Error(`Both agent and Gemini fallback failed`);
      }

      const geminiData = await geminiResponse.json();
      const responseText = geminiData.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated';

      // Stream the response
      const words = responseText.split(' ');
      for (let i = 0; i < words.length; i += 3) {
        const chunk = words.slice(i, i + 3).join(' ') + (i + 3 < words.length ? ' ' : '');
        yield `data: {"type": "chunk", "content": "${chunk.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
        await new Promise(resolve => setTimeout(resolve, 30));
      }

      yield `data: {"type": "end", "message": "Complete (via Gemini)", "sessionId": "${finalSessionId}"}\n\n`;
      return;
    }

    // Process successful agent response
    const data = await response.json();
    const responseText = data.output?.text || data.text || data.response || JSON.stringify(data);

    // Stream the response
    const words = responseText.split(' ');
    for (let i = 0; i < words.length; i += 3) {
      const chunk = words.slice(i, i + 3).join(' ') + (i + 3 < words.length ? ' ' : '');
      yield `data: {"type": "chunk", "content": "${chunk.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"}\n\n`;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    yield `data: {"type": "end", "message": "Complete", "sessionId": "${finalSessionId}"}\n\n`;

  } catch (error) {
    console.error('Stream error:', error);
    yield `data: {"type": "error", "message": "${error instanceof Error ? error.message : 'Unknown error'}"}\n\n`;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: StreamRequest = await request.json();
    const { message, agentId, sessionId, userAccessToken } = body;

    if (!message || !agentId) {
      return NextResponse.json(
        { error: 'Message and agentId are required' },
        { status: 400 }
      );
    }

    // Get user information
    const userInfo = getUserFromIAPHeaders(request);
    const userId = userInfo.userId || `user-${Date.now()}`;

    console.log(`Streaming agent query from user: ${userInfo.email} (${userInfo.userId})`);

    // Use cached session if available
    const cachedSession = await getCachedSession(userId, agentId);
    const currentSessionId: string = sessionId || cachedSession || `session_${Math.random().toString(36).substring(2, 9)}`;
    console.log(`Using session: ${JSON.stringify({ userId, agentId, sessionId: currentSessionId })}`);

    // Create the streaming response
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();

        try {
          const res = streamAgentQuery(message, agentId, userId, currentSessionId, userAccessToken, userInfo.email);
          console.log('Starting stream for user:', userInfo.email)
          for await (const chunk of res) {
            controller.enqueue(encoder.encode(chunk));
          }
        } catch (error) {
          console.error('Streaming error:', error);
          const errorChunk = `data: {"type": "error", "message": "Stream interrupted"}\n\n`;
          controller.enqueue(encoder.encode(errorChunk));
        } finally {
          controller.close();
        }
      },
    });

    return createStreamResponse(stream);

  } catch (error) {
    console.error('Error in agent-engine-stream API:', error);
    return NextResponse.json(
      { error: 'Failed to stream agent response', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

// OPTIONS handler for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}