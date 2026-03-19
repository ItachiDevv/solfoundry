import { get, post } from "./client";

export interface Agent {
  id: string;
  name: string;
  description: string;
  category: "code_review" | "testing" | "documentation" | "security" | "optimization";
  status: "active" | "inactive" | "beta";
  rating: number;
  total_runs: number;
  price_per_run: number;
  creator_wallet: string;
  capabilities: string[];
  icon_url: string | null;
  created_at: string;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
}

export interface AgentRun {
  id: string;
  agent_id: string;
  bounty_id: string;
  status: "queued" | "running" | "completed" | "failed";
  result: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export const agentsApi = {
  list(params?: { category?: string; status?: string; search?: string }) {
    return get<AgentListResponse>("/api/agents", params);
  },

  getById(id: string) {
    return get<Agent>(`/api/agents/${id}`);
  },

  run(agentId: string, bountyId: string) {
    return post<AgentRun>(`/api/agents/${agentId}/run`, {
      bounty_id: bountyId,
    });
  },

  getRunStatus(agentId: string, runId: string) {
    return get<AgentRun>(`/api/agents/${agentId}/runs/${runId}`);
  },
};
