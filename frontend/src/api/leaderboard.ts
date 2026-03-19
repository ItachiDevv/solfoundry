import { get } from "./client";

export interface LeaderboardEntry {
  rank: number;
  wallet_address: string;
  username: string | null;
  avatar_url: string | null;
  reputation: number;
  bounties_completed: number;
  total_earned: number;
  streak_days: number;
  badges: string[];
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total: number;
  period: "all_time" | "monthly" | "weekly";
}

export const leaderboardApi = {
  getLeaderboard(params?: {
    period?: "all_time" | "monthly" | "weekly";
    page?: number;
    page_size?: number;
  }) {
    return get<LeaderboardResponse>("/api/leaderboard", params);
  },

  getContributorStats(wallet: string) {
    return get<LeaderboardEntry>(`/api/leaderboard/${wallet}`);
  },
};
