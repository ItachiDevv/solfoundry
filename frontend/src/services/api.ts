/**
 * API client — fetch wrapper with env base URL, auth headers, retry, and cache.
 * @module services/api
 */
const BASE = (import.meta as Record<string, Record<string, string>>).env?.VITE_API_BASE_URL ?? '';
const cache = new Map<string, { data: unknown; exp: number }>();

/** Build headers with auth token when available. */
function hdrs(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json', ...extra };
  try { const t = localStorage.getItem('solfoundry_token'); if (t) h['Authorization'] = `Bearer ${t}`; } catch {}
  return h;
}

/** Fetch with retry on 5xx/network errors (2 retries, exponential backoff). */
export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const cfg: RequestInit = { ...options, headers: hdrs(options.headers as Record<string, string>) };
  let last: Error | null = null;
  for (let i = 0; i <= 2; i++) {
    try {
      const r = await fetch(`${BASE}${endpoint}`, cfg);
      if (r.ok) return (await r.json()) as T;
      if (r.status >= 500 && i < 2) { last = new Error(`${r.status}`); await new Promise(ok => setTimeout(ok, 500*(i+1))); continue; }
      throw new Error(`API request failed: ${r.status} ${r.statusText}`);
    } catch (e) {
      if (e instanceof TypeError && i < 2) { last = e; await new Promise(ok => setTimeout(ok, 500*(i+1))); continue; }
      throw e instanceof Error ? e : new Error(String(e));
    }
  }
  throw last ?? new Error('Request failed');
}

/** Cached GET — returns cached data when fresh, otherwise fetches and caches. */
export async function cachedGet<T>(endpoint: string, ttl = 30000): Promise<T> {
  const h = cache.get(endpoint);
  if (h && h.exp > Date.now()) return h.data as T;
  const d = await apiFetch<T>(endpoint);
  cache.set(endpoint, { data: d, exp: Date.now() + ttl });
  return d;
}

/** Clear one or all cache entries. */
export function invalidateCache(key?: string): void { key ? cache.delete(key) : cache.clear(); }
