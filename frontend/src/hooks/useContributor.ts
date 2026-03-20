/**
 * useContributor - Fetches a contributor profile by username.
 * Falls back to a minimal GitHub-based profile when the API is unreachable.
 * @module hooks/useContributor
 */
import { useState, useEffect } from 'react';
import { apiFetch } from '../services/api';

/** Contributor profile data. */
export interface ContributorData {
  id: string; username: string; displayName: string; avatarUrl: string;
  walletAddress: string; totalEarned: number; bountiesCompleted: number;
  reputationScore: number; skills: string[]; joinedAt: string;
}

/** Return type of useContributor. */
interface UseContributorResult {
  contributor: ContributorData | null; loading: boolean;
  error: string | null; refetch: () => void;
}

/** Build a minimal fallback profile from just a username. */
function fallbackProfile(username: string): ContributorData {
  return {
    id: username, username, displayName: username,
    avatarUrl: `https://avatars.githubusercontent.com/${username}`,
    walletAddress: '', totalEarned: 0, bountiesCompleted: 0,
    reputationScore: 0, skills: [], joinedAt: new Date().toISOString(),
  };
}

/**
 * Fetch contributor profile from GET /api/contributors?search=username.
 * @param username - GitHub username to look up.
 * @returns Loading state, contributor data, error, and refetch function.
 */
export function useContributor(username: string): UseContributorResult {
  const [contributor, setContributor] = useState<ContributorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState(0);

  useEffect(() => {
    if (!username) { setLoading(false); return; }
    let cancelled = false;
    setLoading(true); setError(null);
    (async () => {
      try {
        const res = await apiFetch<{ items: ContributorData[]; total: number }>(
          `/api/contributors?search=${encodeURIComponent(username)}&limit=1`,
        );
        if (!cancelled) setContributor(res.items.length > 0 ? res.items[0] : fallbackProfile(username));
      } catch (err) {
        if (!cancelled) { setError(err instanceof Error ? err.message : 'Failed'); setContributor(fallbackProfile(username)); }
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [username, key]);

  return { contributor, loading, error, refetch: () => setKey(k => k + 1) };
}
