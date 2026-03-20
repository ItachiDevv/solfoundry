import { useState, useEffect } from 'react';
import type { BountyDetail } from '../types/bountyDetail';
import { mockBountyDetail } from '../data/mockBountyDetail';
export function useBountyDetail(bountyId: string) {
  const [bounty, setBounty] = useState<BountyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      if (bountyId === mockBountyDetail.id) { setBounty(mockBountyDetail); setError(null); }
      else { setBounty(null); setError('Bounty not found'); }
      setLoading(false);
    }, 100);
    return () => clearTimeout(timer);
  }, [bountyId]);
  return { bounty, loading, error };
}
