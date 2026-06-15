import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders, getUserFromIAPHeaders } from '@/utils/auth';

// Cache for agents data
const agentsCache: {
  data: AgentData[] | null;
  timestamp: number;
  isUpdating: boolean;
} = {
  data: null,
  timestamp: 0,
  isUpdating: false,
};

interface AgentData {
  id: string;
  display_name: string;
  description: string;
  create_time: string;
  update_time: string;
  state: string;
}

interface DiscoveryEngineAgent {
  name?: string;
  displayName?: string;
  description?: string;
  createTime?: string;
  updateTime?: string;
  state?: string;
}


const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

/**
 * Fetch agents from Vertex AI Reasoning Engines (Agent Engine/ADK agents)
 */
async function fetchAgentsFromAPI(headers?: HeadersInit): Promise<{ agents: AgentData[]; success: boolean; error?: string }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    // Use provided headers or fall back to service account
    const authHeaders = headers || await getAuthHeaders();
    // Use Vertex AI Reasoning Engines API (Agent Engine/ADK agents)
    const url = `https://${location}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${location}/reasoningEngines`;

    console.log(`Fetching Reasoning Engines from: ${url}`);

    const response = await fetch(url, {
      method: 'GET',
      headers: authHeaders
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Failed to fetch reasoning engines: ${response.status}`, errorText);

      // If 404, no agents exist yet
      if (response.status === 404) {
        return { agents: [], success: true };
      }

      throw new Error(`API call failed: ${response.status} ${response.statusText}`);
    }

    const data: { reasoningEngines?: DiscoveryEngineAgent[] } = await response.json();
    const agents: AgentData[] = [];

    if (data.reasoningEngines) {
      for (const agent of data.reasoningEngines) {
        try {
          const agentData: AgentData = {
            id: agent.name ? agent.name.split('/').pop() || '' : '',
            display_name: agent.displayName || '',
            description: agent.description || '',
            create_time: agent.createTime || '',
            update_time: agent.updateTime || '',
            state: agent.state || 'ACTIVE'
          };

          // Only include agents with display names
          if (agentData.display_name) {
            agents.push(agentData);
            console.log(`Found agent: ${agentData.display_name} (${agentData.id})`);
          }
        } catch (error) {
          console.error('Error parsing agent:', error);
          continue;
        }
      }
    }

    console.log(`Total agents found: ${agents.length}`);

    return {
      agents,
      success: true
    };

  } catch (error) {
    console.error('Error fetching agents from API:', error);
    return {
      agents: [],
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

async function updateAgentsCache() {
  if (agentsCache.isUpdating) {
    return; // Already updating
  }

  agentsCache.isUpdating = true;

  try {
    const result = await fetchAgentsFromAPI();
    if (result.success) {
      agentsCache.data = result.agents;
      agentsCache.timestamp = Date.now();
    }
  } catch (error) {
    console.error('Failed to update agents cache:', error);
  } finally {
    agentsCache.isUpdating = false;
  }
}

// Start periodic cache updates (every 5 minutes)
if (!(globalThis as Record<string, unknown>).agentsCacheInterval) {
  (globalThis as Record<string, unknown>).agentsCacheInterval = setInterval(updateAgentsCache, CACHE_DURATION);
}

export async function GET(request: NextRequest) {
  try {
    const now = Date.now();
    const cacheAge = now - agentsCache.timestamp;
    const isCacheValid = agentsCache.data && cacheAge < CACHE_DURATION;

    // If cache is valid, return cached data
    if (isCacheValid) {
      return NextResponse.json({
        agents: agentsCache.data,
        success: true,
        cached: true,
        cacheAge: cacheAge
      });
    }

    // If cache is invalid but we have old data, return it while updating in background
    if (agentsCache.data && !agentsCache.isUpdating) {
      // Start background update
      updateAgentsCache();

      return NextResponse.json({
        agents: agentsCache.data,
        success: true,
        cached: true,
        stale: true,
        cacheAge: cacheAge
      });
    }

    // If no cache data or already updating, fetch fresh data
    try {
      // Get user context from IAP for logging
      const userInfo = getUserFromIAPHeaders(request);
      console.log(`Fetching agents for user: ${userInfo.email}`);
      
      // Use service account credentials
      const headers = await getAuthHeaders();
      const result = await fetchAgentsFromAPI(headers);

      if (result.success) {
        agentsCache.data = result.agents;
        agentsCache.timestamp = now;

        return NextResponse.json({
          agents: result.agents,
          success: true,
          cached: false
        });
      } else {
        throw new Error(result.error);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';

      console.error('Error fetching agents:', {
        error: errorMessage,
        projectId: process.env.GOOGLE_CLOUD_PROJECT,
        nodeEnv: process.env.NODE_ENV
      });

      // If we have stale cache data, return it with error flag
      if (agentsCache.data) {
        return NextResponse.json({
          agents: agentsCache.data,
          success: true,
          cached: true,
          stale: true,
          error: `Fresh fetch failed: ${errorMessage}`
        });
      }

      // No cache data available, return error
      return NextResponse.json(
        {
          error: errorMessage,
          success: false,
          projectId: process.env.GOOGLE_CLOUD_PROJECT,
          nodeEnv: process.env.NODE_ENV
        },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Error in GET /api/agents:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

// POST endpoint for manual cache refresh
export async function POST() {
  try {
    const result = await fetchAgentsFromAPI();

    if (result.success) {
      agentsCache.data = result.agents;
      agentsCache.timestamp = Date.now();

      return NextResponse.json({
        agents: result.agents,
        success: true,
        refreshed: true
      });
    } else {
      return NextResponse.json(
        { error: result.error },
        { status: 500 }
      );
    }
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

    return NextResponse.json(
      {
        error: errorMessage || 'Failed to refresh Agent Engine agents',
      },
      { status: 500 }
    );
  }
}