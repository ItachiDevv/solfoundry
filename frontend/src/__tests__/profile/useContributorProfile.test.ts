import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useContributorProfile } from '../../hooks/useContributorProfile';
import { mockContributorProfile } from '../../data/mockProfile';

describe('useContributorProfile', () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it('returns null profile when no username given', () => {
    const { result } = renderHook(() => useContributorProfile({}));
    expect(result.current.profile).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('fetches and returns profile data on success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(mockContributorProfile) } as Response);
    const { result } = renderHook(() => useContributorProfile({ username: 'contributor42' }));
    await waitFor(() => { expect(result.current.loading).toBe(false); });
    expect(result.current.profile).toEqual(mockContributorProfile);
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/contributors/contributor42');
  });

  it('sets error on 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 404 } as Response);
    const { result } = renderHook(() => useContributorProfile({ username: 'x' }));
    await waitFor(() => { expect(result.current.loading).toBe(false); });
    expect(result.current.error).toContain('not found');
  });

  it('sets error on 500', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 500 } as Response);
    const { result } = renderHook(() => useContributorProfile({ username: 'x' }));
    await waitFor(() => { expect(result.current.loading).toBe(false); });
    expect(result.current.error).toContain('500');
  });

  it('handles network errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network failure'));
    const { result } = renderHook(() => useContributorProfile({ username: 'x' }));
    await waitFor(() => { expect(result.current.loading).toBe(false); });
    expect(result.current.error).toBe('Network failure');
  });

  it('encodes special characters in username', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(mockContributorProfile) } as Response);
    renderHook(() => useContributorProfile({ username: 'user/special chars' }));
    await waitFor(() => { expect(globalThis.fetch).toHaveBeenCalledWith('/api/contributors/user%2Fspecial%20chars'); });
  });
});
