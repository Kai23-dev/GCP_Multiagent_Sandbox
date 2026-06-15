import { NextRequest, NextResponse } from 'next/server';
import { callGoogleCloudAPI, getUserFromIAPHeaders } from '@/utils/auth';

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'sco-agents-p-3jvh';
const LOCATION = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

interface VertexAIRequest {
  prompt: string;
  model?: string;
  temperature?: number;
  maxOutputTokens?: number;
  topP?: number;
  topK?: number;
}

export async function POST(request: NextRequest) {
  try {
    const { 
      prompt, 
      model = 'gemini-2.0-flash',
      temperature = 0.7,
      maxOutputTokens = 1024,
      topP = 0.8,
      topK = 40
    }: VertexAIRequest = await request.json();

    if (!prompt) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }

    // Get user context from IAP
    const userInfo = getUserFromIAPHeaders(request);
    console.log(`Vertex AI request from user: ${userInfo.email}`);

    // Call Vertex AI Generative AI API
    const vertexUrl = `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${model}:generateContent`;

    const requestBody = {
      contents: [
        {
          role: 'user',
          parts: [
            {
              text: prompt
            }
          ]
        }
      ],
      generationConfig: {
        temperature,
        maxOutputTokens,
        topP,
        topK,
      },
      safetySettings: [
        {
          category: 'HARM_CATEGORY_HATE_SPEECH',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE'
        },
        {
          category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE'
        },
        {
          category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE'
        },
        {
          category: 'HARM_CATEGORY_HARASSMENT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE'
        }
      ]
    };

    // Use service account credentials with user context
    const response = await callGoogleCloudAPI(
      vertexUrl,
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      },
      userInfo.email
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Vertex AI API error:', errorText);
      return NextResponse.json(
        { error: 'Failed to query Vertex AI', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    const responseText = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response received';
    
    return NextResponse.json({
      response: responseText,
      usage: data.usageMetadata,
      safetyRatings: data.candidates?.[0]?.safetyRatings,
      finishReason: data.candidates?.[0]?.finishReason,
    });

  } catch (error) {
    console.error('Error calling Vertex AI:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
