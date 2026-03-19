import { get, post, put } from "./client";

export interface UserProfile {
  id: string;
  wallet_address: string;
  username: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: "contributor" | "maintainer" | "admin";
  reputation: number;
  bounties_created: number;
  bounties_completed: number;
  total_earned: number;
  total_paid: number;
  created_at: string;
  github_username: string | null;
  twitter_handle: string | null;
}

export interface UpdateProfilePayload {
  username?: string;
  bio?: string;
  avatar_url?: string;
  github_username?: string;
  twitter_handle?: string;
}

export const authApi = {
  getNonce(wallet: string) {
    return get<{ nonce: string }>(`/api/auth/nonce?wallet=${wallet}`);
  },

  verify(payload: { wallet: string; signature: number[]; nonce: string }) {
    return post<{ token: string; user: UserProfile }>(
      "/api/auth/verify",
      payload,
    );
  },

  getProfile() {
    return get<UserProfile>("/api/auth/profile");
  },

  updateProfile(payload: UpdateProfilePayload) {
    return put<UserProfile>("/api/auth/profile", payload);
  },

  getProfileByWallet(wallet: string) {
    return get<UserProfile>(`/api/users/${wallet}`);
  },
};
