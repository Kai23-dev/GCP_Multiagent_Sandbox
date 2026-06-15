import { NextRequest, NextResponse } from 'next/server';
import { getUserFromIAPHeaders } from '@/utils/auth';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { PredictionServiceClient } = require('@google-cloud/aiplatform').v1;

interface AgentEngineRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  userAccessToken?: string;
  clearSession?: boolean;
}

/**
 * Query Agent Engine using the Google Cloud AI Platform Node.js client library
 */
export async function POST(request: NextRequest) {
  try {
    const body: AgentEngineRequest = await request.json();
    const { message, agentId, sessionId } = body;

    if (!message || !agentId) {
      return NextResponse.json(
        { error: 'Message and agentId are required' },
        { status: 400 }
      );
    }

    // Get user information
    const userInfo = getUserFromIAPHeaders(request);
    const userId = userInfo.userId || `user-${Date.now()}`;

    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Use existing session or create new one
    const currentSessionId = sessionId || `session-${userId}-${Date.now()}`;

    // Initialize the client
    const predictionClient = new PredictionServiceClient({
      apiEndpoint: `${location}-aiplatform.googleapis.com`,
    });

    // Construct the endpoint name for the reasoning engine
    const endpoint = `projects/${projectId}/locations/${location}/endpoints/${agentId}`;

    try {
      // First, try as a standard prediction endpoint
      const [response] = await predictionClient.predict({
        endpoint: endpoint,
        instances: [{ content: message }],
        parameters: {
          temperature: 0.7,
          maxOutputTokens: 1000,
        },
      });

      const prediction = response.predictions?.[0];
      const responseText = prediction?.content || prediction?.text || JSON.stringify(prediction);

      return NextResponse.json({
        response: responseText,
        sessionId: currentSessionId,
        success: true,
      });

    } catch {
      console.log('Standard prediction failed, trying reasoning engine format...');

      // Try the reasoning engine specific format
      try {
        // For reasoning engines, we need to use a different client approach
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { ReasoningEngineExecutionServiceClient } = require('@google-cloud/aiplatform').v1beta1;

        const reasoningClient = new ReasoningEngineExecutionServiceClient({
          apiEndpoint: `${location}-aiplatform.googleapis.com`,
        });

        const reasoningEngineName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;

        // Try with the query method
        const queryRequest = {
          name: reasoningEngineName,
          input: {
            fields: {
              message: {
                stringValue: message,
              },
              user_id: {
                stringValue: userId,
              },
              session_id: {
                stringValue: currentSessionId,
              },
            },
          },
        };

        const [queryResponse] = await reasoningClient.queryReasoningEngine(queryRequest);

        // Extract the response from the output struct
        let responseText = 'No response';
        if (queryResponse?.output?.fields) {
          const outputFields = queryResponse.output.fields;
          responseText = outputFields.text?.stringValue ||
                        outputFields.response?.stringValue ||
                        outputFields.output?.stringValue ||
                        JSON.stringify(outputFields);
        } else if (queryResponse?.output) {
          responseText = JSON.stringify(queryResponse.output);
        }

        return NextResponse.json({
          response: responseText,
          sessionId: currentSessionId,
          success: true,
        });

      } catch (reasoningError: unknown) {
        console.error('Reasoning engine query failed:', (reasoningError as Error).message);

        // Try streamQuery as a last resort
        try {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const { ReasoningEngineExecutionServiceClient } = require('@google-cloud/aiplatform').v1beta1;

          const reasoningClient = new ReasoningEngineExecutionServiceClient({
            apiEndpoint: `${location}-aiplatform.googleapis.com`,
          });

          const reasoningEngineName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;

          // streamQuery request
          const streamRequest = {
            name: reasoningEngineName,
            input: {
              fields: {
                message: {
                  stringValue: message,
                },
                user_id: {
                  stringValue: userId,
                },
                session_id: {
                  stringValue: currentSessionId,
                },
              },
            },
          };

          // Stream query returns a stream, so we need to handle it differently
          const stream = reasoningClient.streamQueryReasoningEngine(streamRequest);

          let fullResponse = '';

          return new Promise<NextResponse>((resolve) => {
            stream.on('data', (response: unknown) => {
              const resp = response as Record<string, unknown>;
              const output = resp?.output as Record<string, unknown> | undefined;
              const fields = output?.fields as Record<string, { stringValue?: string }> | undefined;
              if (fields) {
                const chunk = fields.text?.stringValue ||
                             fields.response?.stringValue ||
                             fields.output?.stringValue || '';
                fullResponse += chunk;
              }
            });

            stream.on('end', () => {
              resolve(NextResponse.json({
                response: fullResponse || 'No response received from stream',
                sessionId: currentSessionId,
                success: true,
              }));
            });

            stream.on('error', (error: unknown) => {
              console.error('Stream error:', error);
              resolve(NextResponse.json({
                response: '',
                sessionId: currentSessionId,
                success: false,
                error: `Stream query failed: ${(error as Error).message}`,
              }));
            });
          });

        } catch (streamError: unknown) {
          console.error('Stream query failed:', (streamError as Error).message);

          // Return detailed error information
          return NextResponse.json({
            response: '',
            sessionId: currentSessionId,
            success: false,
            error: `All query methods failed. These ADK agents appear to be session managers only. Error details: ${(streamError as Error).message}`,
            agentType: 'ADK Session Manager',
            availableOperations: ['create_session', 'list_sessions', 'get_session', 'delete_session'],
          });
        }
      }
    }

  } catch (error) {
    console.error('Error in agent-engine-v2 API:', error);
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