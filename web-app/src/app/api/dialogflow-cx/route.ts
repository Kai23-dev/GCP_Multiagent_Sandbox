import { NextRequest, NextResponse } from 'next/server';
import { v3beta1 } from '@google-cloud/dialogflow-cx';
import { v4 as uuidv4 } from 'uuid';
import { getUserFromIAPHeaders } from '@/utils/auth';

const { SessionsClient } = v3beta1;


interface DialogflowCXRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  languageCode?: string;
}

export async function POST(request: NextRequest) {
  try {
    const { message, agentId, sessionId, languageCode = 'en' }: DialogflowCXRequest = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    if (!agentId) {
      return NextResponse.json(
        { error: 'Agent ID is required' },
        { status: 400 }
      );
    }

    // Get user information from IAP headers for logging and session tracking
    const userInfo = getUserFromIAPHeaders(request);
    
    // Generate user-specific session ID if not provided
    const finalSessionId = sessionId || `${userInfo.userId}-${agentId}-${uuidv4()}`;

    console.log(`Dialogflow CX query from user: ${userInfo.email} (${userInfo.userId})`);
    console.log(`Using session ID: ${finalSessionId}`);

    // Get environment variables
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION;

    if (!projectId || !location) {
      return NextResponse.json(
        { error: 'Missing required environment variables: GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION' },
        { status: 500 }
      );
    }

    // Initialize Dialogflow CX client with ADC
    // The client automatically uses Application Default Credentials
    const sessionsClient = new SessionsClient({
      projectId: projectId,
      apiEndpoint: `${location}-dialogflow.googleapis.com`,
      location: location,
    });
    
    console.log(`Dialogflow CX: Calling agent ${agentId} for user ${userInfo.email}`);

    // Build the session path
    const sessionPath = sessionsClient.projectLocationAgentSessionPath(
      projectId,
      location,
      agentId,
      finalSessionId
    );

    // Prepare the query input
    const request_payload = {
      session: sessionPath,
      queryInput: {
        text: {
          text: message,
        },
        languageCode: languageCode,
      },
    };

    // Send the request to Dialogflow CX
    const [response] = await sessionsClient.detectIntent(request_payload);

    // Extract response text
    const responseMessages: string[] = [];
    if (response.queryResult?.responseMessages) {
      for (const msg of response.queryResult.responseMessages) {
        if (msg.text?.text) {
          responseMessages.push(...msg.text.text.filter(text => text));
        }
      }
    }

    // Prepare result
    const result = {
      response: responseMessages.length > 0 ? responseMessages.join(' ') : "No response received",
      sessionId: finalSessionId,
      intent: response.queryResult?.intent?.displayName || null,
      intentDetectionConfidence: response.queryResult?.intentDetectionConfidence || 0.0,
      languageCode: response.queryResult?.languageCode || languageCode,
      parameters: response.queryResult?.parameters ? 
        Object.fromEntries(Object.entries(response.queryResult.parameters)) : {},
      fulfillmentText: response.queryResult?.text || "",
      webhookPayload: response.queryResult?.webhookPayloads?.[0] ? 
        Object.fromEntries(Object.entries(response.queryResult.webhookPayloads[0])) : {},
      success: true
    };

    return NextResponse.json(result);

  } catch (error) {
    console.error('Error calling Dialogflow CX:', error);
    return NextResponse.json(
      { 
        error: 'Failed to process Dialogflow CX request', 
        details: error instanceof Error ? error.message : 'Unknown error',
        success: false
      },
      { status: 500 }
    );
  }
}
