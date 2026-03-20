import { useState, useEffect, useCallback } from 'react';
import type { ContributorProfileData } from '../types/profile';

interface UseContributorProfileOptions { username?: string; }
interface UseContributorProfileReturn { profile: ContributorProfileData | null; loading: boolean; error: string | null; refetch: () => void; }

export function useContributorProfile({ username }: UseContributorProfileOptions): UseContributorProfileReturn {
  const [profile, setProfile] = useState<ContributorProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    if (!username) { setProfile(null); setLoading(false); setError(null); return; }
    setLoading(true); setError(null);
    try {
      const response = await fetch(`/api/contributors/${encodeURIComponent(username)}`);
      if (!response.ok) {
        if (response.status === 404) throw new Error(`Contributor "${username}" not found`);
        throw new Error(`Failed to load profile (${response.status})`);
      }
      const data: ContributorProfileData = await response.json();
      setProfile(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error loading profile';
      setError(message); setProfile(null);
    } finally { setLoading(false); }
  }, [username]);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);
  return { profile, loading, error, refetch: fetchProfile };
}
