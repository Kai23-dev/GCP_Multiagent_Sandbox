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
  resource_name?: string;
  isFallback?: boolean;
}

interface DiscoveryEngineAgent {
  name?: string;
  displayName?: string;
  description?: string;
  createTime?: string;
  updateTime?: string;
  state?: string;
}

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Sandbox fallback agents shown in development mode when GCP is unreachable.
 * These match the agents in the sco-agents-feat-release repo.
 */
const SANDBOX_FALLBACK_AGENTS: AgentData[] = [
  {
    id: 'fallback-trend',
    display_name: 'Trend Agent',
    description: 'Spend trend analysis over time periods and categories',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-financial-leakage',
    display_name: 'Financial Leakage Agent',
    description: 'Identifies unapproved spend, leakage risks and anomalies',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-supplier-classification',
    display_name: 'Supplier Classification Agent',
    description: 'Categorises suppliers by type, risk tier and spend band',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-buyer',
    display_name: 'Buyer Agent',
    description: 'Procurement and purchasing behaviour analysis',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-auditor',
    display_name: 'Auditor Agent',
    description: 'Audit, compliance and control gap analysis',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-visualization',
    display_name: 'Visualization Agent',
    description: 'Generates charts and data visualisations from query results',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
  {
    id: 'fallback-contract-intelligence',
    display_name: 'Contract Intelligence Check',
    description: 'Contract compliance and invoice vs contract deviation analysis',
    create_time: '', update_time: '',
    state: 'SANDBOX_VALIDATION_MODE', isFallback: true,
  },
];

/**
 * Fetch agents from Vertex AI Reasoning Engines (Agent Engine / ADK agents)
 */
async function fetchAgentsFromAPI(headers?: HeadersInit): Promise<{ agents: AgentData[]; success: boolean; error?: string }> {
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

    if (!projectId) {
      throw new Error('GOOGLE_CLOUD_PROJECT environment variable is required');
    }

    const authHeaders = headers || await getAuthHeaders();
    const url = `https://${location}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${location}/reasoningEngines`;

    console.log(`Fetching Reasoning Engines from: ${url}`);

    const response = await fetch(url, { method: 'GET', headers: authHeaders });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Failed to fetch reasoning engines: ${response.status}`, errorText);
      if (response.status === 404) return { agents: [], success: true };
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
            state: agent.state || 'ACTIVE',
            resource_name: agent.name || '',
          };
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
    return { agents, success: true };

  } catch (error) {
    console.error('Error fetching agents from API:', error);
    return { agents: [], success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

async function updateAgentsCache() {
  if (agentsCache.isUpdating) return;
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

// Only start background cache polling when NOT in sandbox fallback mode.
// In fallback/dev mode we never call OAuth, so no polling needed.
const isSandboxFallbackMode =
  process.env.ENABLE_SANDBOX_FALLBACK_AGENTS === 'true' ||
  process.env.NODE_ENV === 'development';

if (!isSandboxFallbackMode && !(globalThis as Record<string, unknown>).agentsCacheInterval) {
  (globalThis as Record<string, unknown>).agentsCacheInterval = setInterval(updateAgentsCache, CACHE_DURATION);
}

export async function GET(request: NextRequest) {
  try {
    // ── Sandbox / development fast-path ──────────────────────────────────────
    // If ENABLE_SANDBOX_FALLBACK_AGENTS=true OR NODE_ENV=development,
    // skip all OAuth/GCP calls entirely and return fallback agents immediately.
    // This avoids Zscaler SSL errors and quota issues on the personal laptop.
    if (isSandboxFallbackMode) {
      console.log('[agents] Sandbox fallback mode active — skipping GCP OAuth');
      return NextResponse.json({
        agents: SANDBOX_FALLBACK_AGENTS,
        success: true,
        isFallback: true,
        mode: 'Manual Validation Mode',
        message: 'Running in Sandbox Validation Mode. No live GCP agents connected.',
      });
    }

    // ── Production path (GCP OAuth + Vertex AI) ───────────────────────────────
    const now = Date.now();
    const cacheAge = now - agentsCache.timestamp;
    const isCacheValid = agentsCache.data && cacheAge < CACHE_DURATION;

    if (isCacheValid) {
      return NextResponse.json({ agents: agentsCache.data, success: true, cached: true, cacheAge });
    }

    if (agentsCache.data && !agentsCache.isUpdating) {
      updateAgentsCache();
      return NextResponse.json({ agents: agentsCache.data, success: true, cached: true, stale: true, cacheAge });
    }

    try {
      const userInfo = getUserFromIAPHeaders(request);
      console.log(`Fetching agents for user: ${userInfo.email}`);

      const headers = await getAuthHeaders();
      const result = await fetchAgentsFromAPI(headers);

      if (result.success) {
        agentsCache.data = result.agents;
        agentsCache.timestamp = now;

        // No real agents deployed yet — return sandbox fallback agents
        if (result.agents.length === 0) {
          console.log('No deployed agents found — returning sandbox fallback agents');
          return NextResponse.json({
            agents: SANDBOX_FALLBACK_AGENTS,
            success: true,
            cached: false,
            isFallback: true,
            message: 'No agents deployed yet. Showing Sandbox Validation Mode agents.',
          });
        }

        return NextResponse.json({ agents: result.agents, success: true, cached: false });
      } else {
        throw new Error(result.error);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('GCP fetch failed — falling back to sandbox agents:', { error: errorMessage, nodeEnv: process.env.NODE_ENV });

      // Return stale cache if available
      if (agentsCache.data && agentsCache.data.length > 0) {
        return NextResponse.json({ agents: agentsCache.data, success: true, cached: true, stale: true });
      }

      // Dev mode or GCP unreachable — return fallback, never 500
      return NextResponse.json({
        agents: SANDBOX_FALLBACK_AGENTS,
        success: true,
        isFallback: true,
        message: 'Sandbox Validation Mode — GCP agents not yet reachable.',
      });
    }

  } catch (error) {
    console.error('Error in GET /api/agents:', error);
    // Absolute last resort — still return fallback, not 500
    return NextResponse.json({
      agents: SANDBOX_FALLBACK_AGENTS,
      success: true,
      isFallback: true,
      message: 'Sandbox Validation Mode',
    });
  }
}

// POST endpoint for manual cache refresh
export async function POST() {
  try {
    const result = await fetchAgentsFromAPI();
    if (result.success) {
      agentsCache.data = result.agents;
      agentsCache.timestamp = Date.now();
      return NextResponse.json({ agents: result.agents, success: true, refreshed: true });
    } else {
      return NextResponse.json({ error: result.error }, { status: 500 });
    }
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: errorMessage || 'Failed to refresh agents' }, { status: 500 });
  }
}