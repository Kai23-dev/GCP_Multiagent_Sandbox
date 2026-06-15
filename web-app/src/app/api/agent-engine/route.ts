import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders, getUserFromIAPHeaders } from '@/utils/auth';
import { getCachedSession, clearUserSessions } from '@/utils/session-cache';

interface AgentEngineRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  clearSession?: boolean;
}

// This interface is not used, removing it to fix the warning

/**
 * Query Agent Engine using the REST API
 * Based on: https://cloud.google.com/agent-builder/docs/reference/rest
 */
async function queryAgentWithAPI(
  message: string,
  agentId: string,
  userId: string,
  sessionId?: string,
  userEmail?: string
): Promise<{ response: string; sessionId: string; success: boolean; error?: string; agentType?: string; debug?: unknown }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Get auth headers using service account with ADC
    const headers = await getAuthHeaders();

    // Use existing session or create new one
    const currentSessionId = sessionId || `session-${userId}-${Date.now()}`;

    // Construct the agent resource name
    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;

    // For ADK agents, we need to call the specific class methods
    // First, let's check if this is an ADK agent by getting its details
    const agentUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}`;
    const agentCheckResponse = await fetch(agentUrl, { headers });

    let response;

    if (agentCheckResponse.ok) {
      const agentData = await agentCheckResponse.json();
      const isADKAgent = agentData.spec?.agentFramework === 'google-adk' ||
                         ['607906784857817088', '5846085732698947584', '2701781544422342656', '1788443623507886080'].includes(agentId);

      if (isADKAgent) {
        // ADK agents require the class_method parameter and session management
        console.log('Detected ADK agent - using class_method with session flow');

        const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

        try {
          // First, create or get a session
          let sessionIdToUse = currentSessionId;

          // Create a new session if we don't have one or if it's not a valid ADK session ID
          // Valid ADK session IDs are numeric strings
          const isValidADKSession = sessionIdToUse && /^\d+$/.test(sessionIdToUse);
          if (!isValidADKSession) {
            console.log('Creating new ADK session...');
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
              sessionIdToUse = sessionOutput?.id ||
                             sessionOutput?.session_id ||
                             sessionOutput?.sessionId ||
                             sessionData.output?.id ||
                             sessionData.output?.session_id ||
                             sessionData.output?.sessionId;

              console.log('Created ADK session:', sessionIdToUse);
            } else {
              const error = await createSessionResponse.text();
              console.error('Failed to create session:', error);
              return {
                response: 'Failed to create session with ADK agent',
                sessionId: currentSessionId,
                success: false,
                error: error
              };
            }
          }

          // Now send the actual query using async_stream_query
          console.log('Sending message to ADK agent with session:', sessionIdToUse);
          const requestBody = {
            class_method: 'async_stream_query',
            input: {
              user_id: userEmail || userId,  // Use email for ADK agents
              session_id: sessionIdToUse,
              message: message
            }
          };
          // Use streamQuery endpoint with SSE for async_stream_query
          const streamUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:streamQuery?alt=sse`;
          const queryResponse = await fetch(streamUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify(requestBody)
          });

          if (queryResponse.ok) {
            const responseText = await queryResponse.text();

            // Try parsing as JSON first (streamQuery can return plain JSON)
            try {
              const data = JSON.parse(responseText);

              // Check for the exact format from ADK agents
              if (data.content?.parts?.[0]?.text) {
                return {
                  response: data.content.parts[0].text,
                  sessionId: sessionIdToUse,
                  success: true,
                  agentType: 'ADK Agent'
                };
              }

              // Fallback to other fields
              const output = data.output?.text || data.output?.message || data.output || data.text || data.message;
              if (output) {
                return {
                  response: typeof output === 'string' ? output : JSON.stringify(output),
                  sessionId: sessionIdToUse,
                  success: true,
                  agentType: 'ADK Agent'
                };
              }
            } catch {
              // Not JSON, try SSE format
            }

            // Parse SSE response if it's in that format
            if (responseText.includes('data:')) {
              const lines = responseText.split('\n');
              let finalResponse = '';

              for (const line of lines) {
                if (line.startsWith('data:')) {
                  const jsonStr = line.substring(5).trim();
                  if (jsonStr && jsonStr !== '[DONE]') {
                    try {
                      const data = JSON.parse(jsonStr);
                      if (data.content?.parts?.[0]?.text) {
                        finalResponse += data.content.parts[0].text;
                      } else if (data.text) {
                        finalResponse += data.text;
                      } else if (data.message) {
                        finalResponse += data.message;
                      }
                    } catch {
                      // Continue parsing other lines
                    }
                  }
                }
              }

              if (finalResponse) {
                return {
                  response: finalResponse,
                  sessionId: sessionIdToUse,
                  success: true,
                  agentType: 'ADK Agent'
                };
              }
            }

            // Return raw text if nothing else worked
            return {
              response: responseText,
              sessionId: sessionIdToUse,
              success: true,
              agentType: 'ADK Agent'
            };
          } else {
            const error = await queryResponse.text();
            console.error('ADK agent query failed:', error);
            return {
              response: 'Failed to query ADK agent',
              sessionId: sessionIdToUse,
              success: false,
              error: error
            };
          }
        } catch (e) {
          console.error('Error with ADK agent:', e);
          return {
            response: 'Error connecting to ADK agent',
            sessionId: currentSessionId,
            success: false,
            error: (e as Error).message
          };
        }
      }

      // Check if this is actually a valid agent with query capabilities
      const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

      try {
        const response: Response = await fetch(queryUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            input: {
              query: message
            }
          })
        });

        if (response.ok) {
          const responseText = await response.text();

          // Check if it's newline-delimited JSON (some agents return multiple responses)
          if (responseText.includes('}\n{')) {
            const lines = responseText.split('\n').filter((s: string) => s.trim());
            let finalText = '';

            // Parse each JSON object and find the final text response
            for (const line of lines) {
              try {
                const obj = JSON.parse(line);
                if (obj.content?.parts?.[0]?.text) {
                  finalText = obj.content.parts[0].text;
                }
              } catch {
                // Continue to next line
              }
            }

            if (finalText) {
              return {
                response: finalText.trim(),
                sessionId: currentSessionId,
                success: true,
                agentType: 'Agent'
              };
            }
          }

          // Try to parse as regular JSON
          try {
            const data = JSON.parse(responseText);

            // Check if it's the agent response format with text
            if (data.content?.parts?.[0]?.text) {
              return {
                response: data.content.parts[0].text,
                sessionId: currentSessionId,
                success: true,
                agentType: 'Agent'
              };
            }

            // Check for other output fields
            const output = data.output || data.response || data.result || data.answer || data.text;
            if (output) {
              return {
                response: typeof output === 'string' ? output : JSON.stringify(output),
                sessionId: currentSessionId,
                success: true,
                agentType: 'Agent'
              };
            }

            // If we got any data back, return it
            if (Object.keys(data).length > 0) {
              return {
                response: JSON.stringify(data, null, 2),
                sessionId: currentSessionId,
                success: true,
                agentType: 'Agent'
              };
            }
          } catch {
            // Not valid JSON, return as is if not empty
            if (responseText && responseText.trim()) {
              return {
                response: responseText,
                sessionId: currentSessionId,
                success: true,
                agentType: 'Agent'
              };
            }
          }
        } else {
          const errorText = await response.text();
          console.error('Agent query failed:', response.status, errorText);
          return {
            response: `Failed to query agent. Status: ${response.status}`,
            sessionId: currentSessionId,
            success: false,
            error: errorText
          };
        }
      } catch (e) {
        console.error('Error calling agent:', e);
        return {
          response: 'Error connecting to agent',
          sessionId: currentSessionId,
          success: false,
          error: (e as Error).message
        };
      }
    } else {
        // Not an ADK agent, but still use input struct format
        console.log('Non-ADK agent, using input struct format');

        const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

        // Try with input struct (this is the correct format for Reasoning Engines)
        response = await fetch(queryUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            input: {
              query: message
            }
          }),
        });

    if (!response || !response.ok) {
          // Fallback to simple format
          response = await fetch(queryUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              query: message
            }),
          });
      }
    }

    if (!response || !response.ok) {
      const errorText = response ? await response.text() : 'No response received';
      console.error('All standard query attempts failed');

      // Get agent details to understand its configuration
      const agentUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}`;
      console.log(`Fetching agent details from: ${agentUrl}`);

      const agentResponse = await fetch(agentUrl, { headers });

      if (agentResponse.ok) {
        const agentData = await agentResponse.json();
        console.log('Agent details:', JSON.stringify(agentData, null, 2));

        // Check if the agent has a specific runtime or configuration
        const spec = agentData.spec || {};
        const packageSpec = spec.packageSpec || {};

        // Log the agent configuration to understand how to query it
        console.log('Agent spec:', spec);
        console.log('Package spec:', packageSpec);

        // Try to use the agent's custom runtime if specified
        if (packageSpec.runtimeConfig) {
          console.log('Agent has custom runtime config:', packageSpec.runtimeConfig);
        }

        // For ADK agents, they might use a different invocation pattern
        // Try the execute endpoint which some agents use
        const executeUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:execute`;
        console.log(`Trying execute endpoint: ${executeUrl}`);

        const executeResponse = await fetch(executeUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            query: message,
            parameters: {}
          }),
        });

        if (executeResponse.ok) {
          const executeData = await executeResponse.json();
          console.log('Execute response:', executeData);

          let responseText = '';
          if (executeData.output) {
            responseText = typeof executeData.output === 'string'
              ? executeData.output
              : JSON.stringify(executeData.output, null, 2);
          } else if (executeData.result) {
            responseText = typeof executeData.result === 'string'
              ? executeData.result
              : JSON.stringify(executeData.result, null, 2);
          } else {
            responseText = JSON.stringify(executeData, null, 2);
          }

          return {
            response: responseText,
            sessionId: currentSessionId,
            success: true
          };
        }

        // If execute also fails, try the raw invocation endpoint
        const invokeUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:invoke`;
        console.log(`Trying invoke endpoint: ${invokeUrl}`);

        const invokeResponse = await fetch(invokeUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            input: message
          }),
        });

        if (invokeResponse.ok) {
          const invokeData = await invokeResponse.json();
          console.log('Invoke response:', invokeData);

          return {
            response: JSON.stringify(invokeData, null, 2),
            sessionId: currentSessionId,
            success: true
          };
        }

        // In development, provide a helpful message with agent info
        if (process.env.NODE_ENV === 'development') {
          return {
            response: `Agent "${agentData.displayName || 'AI Agent'}" (ID: ${agentId}) is configured but the query endpoints are not responding as expected.\n\nYour message: "${message}"\n\nAgent configuration:\n${JSON.stringify(spec, null, 2)}\n\nThis agent may require specific invocation methods or the Python SDK. The REST API endpoints for Agent Engine are still in preview.`,
            sessionId: currentSessionId,
            success: true
          };
        }

        return {
          response: `Agent "${agentData.displayName || agentId}" is available but query failed.`,
          sessionId: currentSessionId,
          success: false,
          error: errorText
        };
      }

      throw new Error(`Failed to query agent: ${response?.status}`);
    }

    const data = await response.json();

    // Extract response text from various possible formats
    let responseText = '';

    // Handle different response formats from different endpoints
    if (data.output?.text) {
      // Standard query response
      responseText = data.output.text;
    } else if (data.predictions?.[0]) {
      // Predict endpoint response
      responseText = data.predictions[0].content || JSON.stringify(data.predictions[0]);
    } else if (data.candidates?.[0]?.content?.parts?.[0]?.text) {
      // GenerateContent response (Gemini-style)
      responseText = data.candidates[0].content.parts[0].text;
    } else if (data.result) {
      // Simple result format
      responseText = data.result;
    } else if (data.response) {
      // Direct response format
      responseText = data.response;
    } else if (data.text) {
      // Plain text format
      responseText = data.text;
    } else if (typeof data === 'string') {
      // String response
      responseText = data;
    } else {
      // Unknown format, show the whole response
      console.log('Unknown response format:', data);
      responseText = JSON.stringify(data, null, 2);
    }

    return {
      response: responseText || 'No response from agent',
      sessionId: currentSessionId,
      success: true
    };

  } catch (error) {
    console.error('Error querying agent via API:', error);

    // Provide a helpful error message
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

    // For development, provide mock response to test UI
    if (process.env.NODE_ENV === 'development' && errorMessage.includes('404')) {
      return {
        response: `[Development Mode] Agent Engine APIs are still in preview. Your agent "${agentId}" exists but the query endpoint may not be publicly available yet. In production, this would connect to your deployed agent.`,
        sessionId: sessionId || `session-${userId}-${Date.now()}`,
        success: true
      };
    }

    return {
      response: '',
      sessionId: '',
      success: false,
      error: errorMessage
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: AgentEngineRequest = await request.json();
    const { message, agentId, sessionId, clearSession } = body;

    if (!message || !agentId) {
      return NextResponse.json(
        { error: 'Message and agentId are required' },
        { status: 400 }
      );
    }

    // Get user information from IAP headers for personalized sessions
    const userInfo = getUserFromIAPHeaders(request);

    // Handle session clearing if requested
    if (clearSession) {
      await clearUserSessions();
      console.log(`Cleared sessions for user: ${userInfo.userId}`);
    }

    // Get or create cached session for this user-agent combination
    let userBasedSessionId: string;
    if (sessionId) {
      userBasedSessionId = sessionId;
      console.log(`Using provided session ID: ${sessionId}`);
    } else {
      // Get cached session or create new one
      userBasedSessionId = await getCachedSession(userInfo.userId, agentId);
      console.log(`Using cached session ID: ${userBasedSessionId}`);
    }

    console.log(`Agent query from user: ${userInfo.email} (${userInfo.userId})`);
    console.log(`Session management: cached=${!sessionId}, cleared=${clearSession}`);

    // Query the agent using REST API with service account credentials
    const result = await queryAgentWithAPI(
      message,
      agentId,
      userInfo.userId,
      userBasedSessionId,
      userInfo.email  // Pass email for ADK agents
    );

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || 'Failed to query agent' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      response: result.response,
      sessionId: result.sessionId,
      success: true
    });

  } catch (error) {
    console.error('Error in agent-engine API:', error);
    return NextResponse.json(
      { error: 'Failed to query agent', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}