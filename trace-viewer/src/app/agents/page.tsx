"use client";

import { useEffect, useState } from "react";
import { Save, Plus, Trash2, AlertCircle, CheckCircle } from "lucide-react";

interface AgentEntry {
  key: string;
  displayName: string;
  workloadId: string;
  resourceName?: string;
  isOrchestrator?: boolean;
}

interface AgentRegistry {
  env: string;
  updatedAt: string;
  agents: AgentEntry[];
}

interface StorageInfo {
  type: string;
  projectId: string;
  collection: string;
  doc: string;
  database: string;
  configured: boolean;
}

export default function AgentsAdminPage() {
  const [registry, setRegistry] = useState<AgentRegistry | null>(null);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadRegistry();
  }, []);

  async function loadRegistry() {
    setLoading(true);
    try {
      const res = await fetch("/api/agent-registry");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to load");
      setRegistry(data.registry);
      setStorage(data.storage);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!registry) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch("/api/agent-registry", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(registry),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to save");
      setRegistry(data.registry);
      setMessage({
        type: "success",
        text: data.warning ? `Saved (in-memory). ${data.warning}` : "Registry saved successfully",
      });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  }

  function updateEntry(idx: number, patch: Partial<AgentEntry>) {
    if (!registry) return;
    const newAgents = [...registry.agents];
    newAgents[idx] = { ...newAgents[idx], ...patch };
    setRegistry({ ...registry, agents: newAgents });
  }

  function addEntry() {
    if (!registry) return;
    setRegistry({
      ...registry,
      agents: [...registry.agents, { key: "", displayName: "", workloadId: "" }],
    });
  }

  function deleteEntry(idx: number) {
    if (!registry) return;
    setRegistry({
      ...registry,
      agents: registry.agents.filter((_, i) => i !== idx),
    });
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading registry...</div>;
  }

  if (!registry) {
    return <div className="p-8 text-center text-red-500">Failed to load registry</div>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-800">Agent Registry</h1>
        <p className="text-sm text-gray-500 mt-1">
          Map agent keys to their Vertex AI reasoning engine workload IDs. These IDs are used to fetch
          logs and spans from sub-agent workloads so the full end-to-end trace is visible.
        </p>
      </div>

      {/* Message */}
      {message && (
        <div className={`rounded-lg border p-3 flex items-center gap-2 text-sm ${
          message.type === "success"
            ? "bg-emerald-50 border-emerald-200 text-emerald-800"
            : "bg-red-50 border-red-200 text-red-800"
        }`}>
          {message.type === "success"
            ? <CheckCircle className="w-4 h-4" />
            : <AlertCircle className="w-4 h-4" />
          }
          {message.text}
        </div>
      )}

      {/* Agent Table */}
      <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-4 py-3">Agent Key</th>
              <th className="px-4 py-3">Display Name</th>
              <th className="px-4 py-3">Workload ID</th>
              <th className="px-4 py-3 w-24">Orchestrator</th>
              <th className="px-4 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {registry.agents.map((a, i) => (
              <tr key={i}>
                <td className="px-4 py-2">
                  <input
                    value={a.key}
                    onChange={(e) => updateEntry(i, { key: e.target.value })}
                    placeholder="spend_iq_agent"
                    className="w-full px-2 py-1 border rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    value={a.displayName}
                    onChange={(e) => updateEntry(i, { displayName: e.target.value })}
                    placeholder="SpendIQ"
                    className="w-full px-2 py-1 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    value={a.workloadId}
                    onChange={(e) => updateEntry(i, { workloadId: e.target.value })}
                    placeholder="9219968498610995200"
                    className="w-full px-2 py-1 border rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </td>
                <td className="px-4 py-2 text-center">
                  <input
                    type="checkbox"
                    checked={!!a.isOrchestrator}
                    onChange={(e) => updateEntry(i, { isOrchestrator: e.target.checked })}
                    className="w-4 h-4"
                  />
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => deleteEntry(i)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                    title="Remove"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={addEntry}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white border rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Plus className="w-4 h-4" />
          Add Agent
        </button>
        <div className="flex gap-2">
          <select
            value={registry.env}
            onChange={(e) => setRegistry({ ...registry, env: e.target.value })}
            className="px-3 py-1.5 border rounded-lg text-sm"
          >
            <option value="review">review</option>
            <option value="dev">dev</option>
            <option value="stage">stage</option>
            <option value="prod">prod</option>
          </select>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save Registry"}
          </button>
        </div>
      </div>
    </div>
  );
}
