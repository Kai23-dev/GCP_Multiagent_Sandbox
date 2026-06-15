import { getAccessToken, getProjectId } from "./gcp-auth";

export interface AgentEntry {
  key: string; // e.g. "spend_iq_agent"
  displayName: string; // e.g. "SpendIQ"
  workloadId: string; // e.g. "9219968498610995200"
  resourceName?: string; // Full Vertex AI resource name
  isOrchestrator?: boolean;
}

export interface AgentRegistry {
  env: string;
  updatedAt: string;
  updatedBy?: string;
  agents: AgentEntry[];
}

const DEFAULT_ENV = process.env.AGENT_ENV || "review";
const FIRESTORE_COLLECTION = process.env.AGENT_REGISTRY_COLLECTION || "trace_viewer_config";
const FIRESTORE_DOC = "agent_registry";
const FIRESTORE_DATABASE = process.env.FIRESTORE_DATABASE || "(default)";
const FIRESTORE_BASE = "https://firestore.googleapis.com/v1";
const CACHE_TTL_MS = 60 * 1000; // 60s TTL to reduce Firestore load on hot paths

// In-memory cache with TTL (doubles as fallback when Firestore is unavailable)
let memoryCache: AgentRegistry | null = null;
let cacheLoadedAt = 0;

function firestoreDocUrl(projectId: string): string {
  return `${FIRESTORE_BASE}/projects/${projectId}/databases/${FIRESTORE_DATABASE}/documents/${FIRESTORE_COLLECTION}/${FIRESTORE_DOC}`;
}

const DEFAULT_REGISTRY: AgentRegistry = {
  env: DEFAULT_ENV,
  updatedAt: new Date().toISOString(),
  agents: [
    { key: "spend_iq_agent", displayName: "SpendIQ", workloadId: "", isOrchestrator: true },
    { key: "buyer_agent", displayName: "Buyer", workloadId: "" },
    { key: "trend_agent", displayName: "Trend Analyst", workloadId: "" },
    { key: "supplier_classification_agent", displayName: "Supplier Classification", workloadId: "" },
    { key: "financial_leakage_agent", displayName: "Financial Leakage", workloadId: "" },
    { key: "auditor_agent", displayName: "Auditor", workloadId: "" },
    { key: "visualization_agent", displayName: "Visualization", workloadId: "" },
    { key: "contract_intelligence_agent", displayName: "Contract Intelligence", workloadId: "" },
    { key: "sql_generation_agent", displayName: "SQL Generation", workloadId: "" },
    { key: "validation_agent", displayName: "Validation", workloadId: "" },
    { key: "sql_execution_agent", displayName: "SQL Execution", workloadId: "" },
  ],
};

export async function loadRegistry(options?: { forceRefresh?: boolean }): Promise<AgentRegistry> {
  // Serve from cache if fresh
  if (
    !options?.forceRefresh &&
    memoryCache &&
    Date.now() - cacheLoadedAt < CACHE_TTL_MS
  ) {
    return memoryCache;
  }

  const projectId = getProjectId();
  if (!projectId) {
    if (!memoryCache) memoryCache = { ...DEFAULT_REGISTRY };
    cacheLoadedAt = Date.now();
    return memoryCache;
  }

  try {
    const token = await getAccessToken();
    const resp = await fetch(firestoreDocUrl(projectId), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.status === 404) {
      // Document doesn't exist yet — seed defaults into cache
      memoryCache = { ...DEFAULT_REGISTRY };
      cacheLoadedAt = Date.now();
      return memoryCache;
    }
    if (!resp.ok) {
      console.error("Agent registry Firestore read error:", resp.status);
      if (memoryCache) return memoryCache;
      memoryCache = { ...DEFAULT_REGISTRY };
      cacheLoadedAt = Date.now();
      return memoryCache;
    }
    const doc = await resp.json();
    const jsonString: string | undefined = doc?.fields?.json?.stringValue;
    if (!jsonString) {
      memoryCache = { ...DEFAULT_REGISTRY };
      cacheLoadedAt = Date.now();
      return memoryCache;
    }
    const data = JSON.parse(jsonString) as AgentRegistry;
    memoryCache = data;
    cacheLoadedAt = Date.now();
    return data;
  } catch (err) {
    console.error("Agent registry load error:", err);
    if (memoryCache) return memoryCache;
    memoryCache = { ...DEFAULT_REGISTRY };
    cacheLoadedAt = Date.now();
    return memoryCache;
  }
}

export async function saveRegistry(registry: AgentRegistry): Promise<void> {
  registry.updatedAt = new Date().toISOString();
  memoryCache = registry;
  cacheLoadedAt = Date.now();

  const projectId = getProjectId();
  if (!projectId) {
    throw new Error("GOOGLE_CLOUD_PROJECT env var not set; cannot persist to Firestore");
  }

  const token = await getAccessToken();
  // Use PATCH with updateMask to upsert the 'json' field; create doc if missing
  const url = firestoreDocUrl(projectId);
  const body = {
    fields: {
      json: { stringValue: JSON.stringify(registry) },
      updatedAt: { timestampValue: registry.updatedAt },
    },
  };
  const resp = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Firestore save failed: ${resp.status} ${errText}`);
  }
}

export function getStorageInfo(): {
  type: "firestore";
  projectId: string;
  collection: string;
  doc: string;
  database: string;
  configured: boolean;
} {
  const projectId = getProjectId();
  return {
    type: "firestore",
    projectId,
    collection: FIRESTORE_COLLECTION,
    doc: FIRESTORE_DOC,
    database: FIRESTORE_DATABASE,
    configured: Boolean(projectId),
  };
}

/** Look up workload ID by agent key or display name (case-insensitive). */
export function findWorkloadId(registry: AgentRegistry, nameOrKey: string): string | null {
  const lower = nameOrKey.toLowerCase();
  for (const a of registry.agents) {
    if (a.key.toLowerCase() === lower || a.displayName.toLowerCase() === lower) {
      return a.workloadId || null;
    }
  }
  return null;
}

/** Return all workload IDs that have been configured. */
export function allWorkloadIds(registry: AgentRegistry): string[] {
  return registry.agents.map((a) => a.workloadId).filter((w): w is string => Boolean(w));
}
