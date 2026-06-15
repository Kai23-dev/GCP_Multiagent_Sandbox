import { NextResponse } from 'next/server';
import { AgentsClient } from '@google-cloud/dialogflow-cx';

// Cache for dialogflow agents data
const dialogflowAgentsCache: {
  data: DialogflowAgent[] | null;
  timestamp: number;
  isUpdating: boolean;
} = {
  data: null,
  timestamp: 0,
  isUpdating: false,
};

interface DialogflowAgent {
  id: string;
  name: string;
  display_name: string;
  description: string;
  time_zone: string;
  default_language_code: string;
  supported_language_codes: string[];
  avatar_uri: string;
  enable_stackdriver_logging: boolean;
}

interface DialogflowResult {
  agents: DialogflowAgent[];
  success: boolean;
  error?: string;
}

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

async function fetchDialogflowAgentsFromAPI(): Promise<DialogflowResult> {
  try {
    // Get environment variables
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION;

    if (!projectId || !location) {
      throw new Error('Missing required environment variables: GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION');
    }

    // Set quota project environment variable to resolve ADC authentication issue
    // This tells Google Cloud APIs which project to use for quota and billing
    process.env.GOOGLE_CLOUD_QUOTA_PROJECT = projectId;
    process.env.GCLOUD_PROJECT = projectId;
    
    // Initialize Dialogflow CX client with regional endpoint
    const agentsClient = new AgentsClient({
      projectId: projectId,
      apiEndpoint: `${location}-dialogflow.googleapis.com`,
    });

    const parent = `projects/${projectId}/locations/${location}`;
    
    // List all Dialogflow CX agents
    const [agents] = await agentsClient.listAgents({
      parent: parent,
    });
    
    const processedAgents = [];
    for (const agent of agents) {
      // Extract agent ID from the full resource name (e.g., projects/.../agents/agent-id)
      const agentId = agent.name?.split('/').pop() || '';
      
      // Only include agents with display names
      if (agent.displayName && agent.displayName.trim()) {
        processedAgents.push({
          id: agentId,
          name: agent.name || '',  // Full resource name
          display_name: agent.displayName.trim(),
          description: agent.description || '',
          time_zone: agent.timeZone || '',
          default_language_code: agent.defaultLanguageCode || '',
          supported_language_codes: agent.supportedLanguageCodes || [],
          avatar_uri: agent.avatarUri || '',
          enable_stackdriver_logging: agent.enableStackdriverLogging || false,
        });
      }
    }
    
    return {
      agents: processedAgents,
      success: true
    };
    
  } catch (error) {
    console.error('Error fetching Dialogflow CX agents:', error);
    throw {
      error: error instanceof Error ? error.message : 'Failed to fetch Dialogflow CX agents',
      success: false
    };
  }
}

async function updateDialogflowAgentsCache() {
  if (dialogflowAgentsCache.isUpdating) {
    return; // Already updating
  }
  
  dialogflowAgentsCache.isUpdating = true;
  
  try {
    const result = await fetchDialogflowAgentsFromAPI();
    if (result.success) {
      dialogflowAgentsCache.data = result.agents;
      dialogflowAgentsCache.timestamp = Date.now();
    }
  } catch (error) {
    console.error('Failed to update Dialogflow agents cache:', error);
  } finally {
    dialogflowAgentsCache.isUpdating = false;
  }
}

// Start periodic cache updates (every 5 minutes)
if (!(globalThis as Record<string, unknown>).dialogflowAgentsCacheInterval) {
  (globalThis as Record<string, unknown>).dialogflowAgentsCacheInterval = setInterval(updateDialogflowAgentsCache, CACHE_DURATION);
}

export async function GET() {
  try {
    const now = Date.now();
    const cacheAge = now - dialogflowAgentsCache.timestamp;
    const isCacheValid = dialogflowAgentsCache.data && cacheAge < CACHE_DURATION;
    
    // If cache is valid, return cached data
    if (isCacheValid) {
      return NextResponse.json({
        agents: dialogflowAgentsCache.data,
        success: true,
        cached: true,
        cacheAge: cacheAge
      });
    }
    
    // If cache is invalid but we have old data, return it while updating in background
    if (dialogflowAgentsCache.data && !dialogflowAgentsCache.isUpdating) {
      // Start background update
      updateDialogflowAgentsCache();
      
      return NextResponse.json({
        agents: dialogflowAgentsCache.data,
        success: true,
        cached: true,
        stale: true,
        cacheAge: cacheAge
      });
    }
    
    // If no cache data or already updating, fetch fresh data
    try {
      const result = await fetchDialogflowAgentsFromAPI();
      
      if (result.success) {
        dialogflowAgentsCache.data = result.agents;
        dialogflowAgentsCache.timestamp = now;
        
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
      const errorDetails = (error as Record<string, unknown>)?.error || errorMessage;
      
      // If we have stale cache data, return it with error flag
      if (dialogflowAgentsCache.data) {
        return NextResponse.json({
          agents: dialogflowAgentsCache.data,
          success: true,
          cached: true,
          stale: true,
          error: 'Failed to refresh agents, showing cached data'
        });
      }
      
      // No cache data, return error
      return NextResponse.json(
        { 
          error: errorDetails || 'Failed to fetch Dialogflow CX agents',
          details: (error as Record<string, unknown>)?.details,
          stderr: (error as Record<string, unknown>)?.stderr
        },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Error in GET /api/dialogflow-agents:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

// POST endpoint for manual cache refresh
export async function POST() {
  try {
    const result = await fetchDialogflowAgentsFromAPI();
    
    if (result.success) {
      dialogflowAgentsCache.data = result.agents;
      dialogflowAgentsCache.timestamp = Date.now();
      
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
    const errorDetails = (error as Record<string, unknown>)?.error || errorMessage;
    
    return NextResponse.json(
      { 
        error: errorDetails || 'Failed to refresh Dialogflow CX agents',
        details: (error as Record<string, unknown>)?.details,
        stderr: (error as Record<string, unknown>)?.stderr
      },
      { status: 500 }
    );
  }
}
