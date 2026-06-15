import { NextRequest, NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'sco-agents-p-3jvh';
const LOCATION = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

interface DiscoveryEngineRequest {
  query: string;
  dataStoreId: string;
  sessionId?: string;
  filter?: string;
}

export async function POST(request: NextRequest) {
  try {
    const { query, dataStoreId, sessionId, filter }: DiscoveryEngineRequest = await request.json();

    if (!query || !dataStoreId) {
      return NextResponse.json(
        { error: 'Query and dataStoreId are required' },
        { status: 400 }
      );
    }

    // Initialize Google Auth
    const auth = new GoogleAuth({
      scopes: ['https://www.googleapis.com/auth/cloud-platform'],
    });

    const authClient = await auth.getClient();
    const accessToken = await authClient.getAccessToken();

    // Call Discovery Engine Search API
    const searchUrl = `https://discoveryengine.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${dataStoreId}/servingConfigs/default_search:search`;

    const requestBody = {
      query,
      pageSize: 10,
      ...(sessionId && { sessionId }),
      ...(filter && { filter }),
      queryExpansionSpec: {
        condition: 'AUTO',
      },
      spellCorrectionSpec: {
        mode: 'AUTO',
      },
    };

    const response = await fetch(searchUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Discovery Engine API error:', errorText);
      return NextResponse.json(
        { error: 'Failed to query discovery engine', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    return NextResponse.json({
      results: data.results || [],
      totalSize: data.totalSize || 0,
      sessionId: data.sessionId,
      correctedQuery: data.correctedQuery,
      facets: data.facets || [],
    });

  } catch (error) {
    console.error('Error calling Discovery Engine:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
