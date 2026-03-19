import { get, post, put } from "./client";

export interface Bounty {
  id: string;
  title: string;
  description: string;
  reward_amount: number;
  reward_token: string;
  status: "open" | "in_progress" | "review" | "completed" | "cancelled";
  difficulty: "beginner" | "intermediate" | "advanced" | "expert";
  tags: string[];
  creator_wallet: string;
  assignee_wallet: string | null;
  escrow_address: string | null;
  created_at: string;
  updated_at: string;
  deadline: string | null;
  submissions_count: number;
}

export interface BountyListResponse {
  bounties: Bounty[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateBountyPayload {
  title: string;
  description: string;
  reward_amount: number;
  reward_token: string;
  difficulty: Bounty["difficulty"];
  tags: string[];
  deadline: string | null;
}

export interface BountySubmission {
  id: string;
  bounty_id: string;
  contributor_wallet: string;
  description: string;
  pr_url: string | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export const bountiesApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    difficulty?: string;
    search?: string;
    tags?: string[];
  }) {
    return get<BountyListResponse>("/api/bounties", params);
  },

  getById(id: string) {
    return get<Bounty>(`/api/bounties/${id}`);
  },

  create(payload: CreateBountyPayload) {
    return post<Bounty>("/api/bounties", payload);
  },

  update(id: string, payload: Partial<CreateBountyPayload>) {
    return put<Bounty>(`/api/bounties/${id}`, payload);
  },

  submit(id: string, submission: { description: string; pr_url?: string }) {
    return post<BountySubmission>(`/api/bounties/${id}/submissions`, submission);
  },

  getSubmissions(id: string) {
    return get<BountySubmission[]>(`/api/bounties/${id}/submissions`);
  },

  claim(id: string) {
    return post<Bounty>(`/api/bounties/${id}/claim`);
  },

  approve(id: string, submissionId: string) {
    return post<Bounty>(`/api/bounties/${id}/submissions/${submissionId}/approve`);
  },
};
