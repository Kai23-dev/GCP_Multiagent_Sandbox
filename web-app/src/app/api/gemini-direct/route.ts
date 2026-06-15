import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/utils/auth';

/**
 * Direct Gemini API endpoint
 * This bypasses the broken ADK agents and uses Gemini directly
 */
export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    const projectId = process.env.GOOGLE_CLOUD_PROJECT || 'agentspace-prod-w89w';
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';
    const model = 'gemini-1.5-flash';

    // Get auth headers
    const headers = await getAuthHeaders();

    // Call Gemini directly via generateContent endpoint
    const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${model}:generateContent`;

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [
              {
                text: message
              }
            ]
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

    if (!response.ok) {
      const error = await response.text();
      console.error('Gemini API error:', error);
      throw new Error(`Gemini API failed: ${response.status}`);
    }

    const data = await response.json();

    // Extract the text from Gemini's response
    const responseText = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated';

    return NextResponse.json({
      response: responseText,
      sessionId: `gemini-session-${Date.now()}`,
      success: true,
      model: model
    });

  } catch (error) {
    console.error('Error in gemini-direct API:', error);
    return NextResponse.json(
      {
        error: 'Failed to process request',
        details: error instanceof Error ? error.message : 'Unknown error',
        success: false
      },
      { status: 500 }
    );
  }
}