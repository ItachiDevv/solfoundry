/** Tests for frontend-API integration: client, hooks, ErrorBoundary, skeletons. */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import React from 'react';

const orig = globalThis.fetch;
afterEach(() => { globalThis.fetch = orig; vi.restoreAllMocks(); vi.resetModules(); });
const ok = (d: unknown) => ({ ok: true, json: () => Promise.resolve(d) });
const err = (s: number) => ({ ok: false, status: s, statusText: 'E' });

describe('apiFetch', () => {
  it('parses JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ v: 1 }));
    expect(await (await import('../services/api')).apiFetch('/x')).toEqual({ v: 1 });
  });
  it('throws on 404', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(err(404));
    await expect((await import('../services/api')).apiFetch('/x')).rejects.toThrow('404');
  });
  it('retries on 500', async () => {
    let n = 0;
    globalThis.fetch = vi.fn().mockImplementation(() => ++n < 3 ? Promise.resolve(err(500)) : Promise.resolve(ok({ r: 1 })));
    expect(await (await import('../services/api')).apiFetch('/r')).toEqual({ r: 1 });
  });
  it('retries on TypeError', async () => {
    let n = 0;
    globalThis.fetch = vi.fn().mockImplementation(() => ++n < 2 ? Promise.reject(new TypeError('f')) : Promise.resolve(ok({})));
    await (await import('../services/api')).apiFetch('/n'); expect(n).toBe(2);
  });
  it('sends auth token', async () => {
    const mf = vi.fn().mockResolvedValue(ok({}));
    globalThis.fetch = mf; vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('tok');
    await (await import('../services/api')).apiFetch('/a');
    expect(mf.mock.calls[0][1].headers['Authorization']).toBe('Bearer tok');
  });
  it('caches', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ c: 1 }));
    const m = await import('../services/api'); m.invalidateCache();
    await m.cachedGet('/c', 60000); await m.cachedGet('/c', 60000);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

describe('ErrorBoundary', () => {
  it('renders children', async () => {
    const { ErrorBoundary } = await import('../components/ErrorBoundary');
    render(<ErrorBoundary><span>ok</span></ErrorBoundary>);
    expect(screen.getByText('ok')).toBeTruthy();
  });
  it('catches errors', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const { ErrorBoundary } = await import('../components/ErrorBoundary');
    render(<ErrorBoundary>{React.createElement(() => { throw new Error('boom'); })}</ErrorBoundary>);
    expect(screen.getByText('boom')).toBeTruthy();
  });
});

describe('LoadingSkeleton', () => {
  it('renders grid', async () => {
    const { GridSkeleton } = await import('../components/LoadingSkeleton');
    expect(render(<GridSkeleton count={3} />).container.querySelectorAll('.rounded-xl').length).toBe(3);
  });
  it('has status role', async () => {
    const { PageSkeleton } = await import('../components/LoadingSkeleton');
    render(<PageSkeleton label="L" />); expect(screen.getByRole('status')).toBeTruthy();
  });
});

describe('useContributor', () => {
  it('fetches data', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ items: [{ id: '1', username: 'a', displayName: 'A', avatarUrl: '', walletAddress: '', totalEarned: 9, bountiesCompleted: 1, reputationScore: 5, skills: [], joinedAt: '' }], total: 1 }));
    const { result } = renderHook(() => require('../hooks/useContributor').useContributor('a'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.contributor?.totalEarned).toBe(9);
  });
  it('fallback on error', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('x'));
    const { result } = renderHook(() => require('../hooks/useContributor').useContributor('b'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.contributor?.username).toBe('b');
  });
  it('empty username', async () => {
    const { result } = renderHook(() => require('../hooks/useContributor').useContributor(''));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.contributor).toBeNull();
  });
});
