import { useState, useEffect } from 'react';
import type { TokenomicsData, TreasuryStats } from '../types/tokenomics';
import { apiFetch } from '../services/api';

/** Default tokenomics shown while API data loads (zero values). */
const DEFAULT_TOKENOMICS: TokenomicsData = {
  tokenName: 'FNDRY', tokenCA: 'C2TvY8E8B75EF2UP8cTpTp3EDUjTgjWmpaGnT74VBAGS',
  totalSupply: 1_000_000_000, circulatingSupply: 0, treasuryHoldings: 0,
  totalDistributed: 0, totalBuybacks: 0, totalBurned: 0, feeRevenueSol: 0,
  lastUpdated: new Date().toISOString(), distributionBreakdown: {},
};

/** Default treasury stats shown while API data loads (zero values). */
const DEFAULT_TREASURY: TreasuryStats = {
  solBalance: 0, fndryBalance: 0, treasuryWallet: '57uMiMHnRJCxM7Q1MdGVMLsEtxzRiy1F6qKFWyP1S9pp',
  totalPaidOutFndry: 0, totalPaidOutSol: 0, totalPayouts: 0,
  totalBuybackAmount: 0, totalBuybacks: 0, lastUpdated: new Date().toISOString(),
};

/**
 * Fetches live tokenomics and treasury data via apiFetch with retry.
 * Falls back to zero-value defaults when the API is unreachable.
 */
export function useTreasuryStats() {
  const [tokenomics, setTokenomics] = useState<TokenomicsData>(DEFAULT_TOKENOMICS);
  const [treasury, setTreasury] = useState<TreasuryStats>(DEFAULT_TREASURY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [t, tr] = await Promise.all([
          apiFetch<TokenomicsData>('/api/tokenomics'),
          apiFetch<TreasuryStats>('/api/treasury'),
        ]);
        if (!cancelled) { setTokenomics(t); setTreasury(tr); }
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load'); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  return { tokenomics, treasury, loading, error };
}
