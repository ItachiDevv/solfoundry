import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { apiClient } from "../api/client";

interface User {
  id: string;
  walletAddress: string;
  username: string | null;
  avatarUrl: string | null;
  role: "contributor" | "maintainer" | "admin";
  reputation: number;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "solfoundry-auth-token";
const USER_KEY = "solfoundry-auth-user";

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { publicKey, signMessage, connected, disconnect } = useWallet();
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [token, setToken] = useState<string | null>(getStoredToken);
  const [isLoading, setIsLoading] = useState(false);

  const isAuthenticated = useMemo(
    () => !!token && !!user && connected,
    [token, user, connected],
  );

  // Sync token to API client
  useEffect(() => {
    if (token) {
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      delete apiClient.defaults.headers.common["Authorization"];
      localStorage.removeItem(TOKEN_KEY);
    }
  }, [token]);

  // Persist user
  useEffect(() => {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  }, [user]);

  // Clear auth if wallet disconnects
  useEffect(() => {
    if (!connected && token) {
      setToken(null);
      setUser(null);
    }
  }, [connected, token]);

  const login = useCallback(async () => {
    if (!publicKey || !signMessage) return;

    setIsLoading(true);
    try {
      // Request a nonce from the backend
      const nonceRes = await apiClient.get<{ nonce: string }>(
        `/api/auth/nonce?wallet=${publicKey.toBase58()}`,
      );
      const { nonce } = nonceRes.data;

      // Sign the nonce
      const message = new TextEncoder().encode(
        `Sign in to SolFoundry\nNonce: ${nonce}`,
      );
      const signature = await signMessage(message);

      // Verify signature and get JWT
      const authRes = await apiClient.post<{ token: string; user: User }>(
        "/api/auth/verify",
        {
          wallet: publicKey.toBase58(),
          signature: Array.from(signature),
          nonce,
        },
      );

      setToken(authRes.data.token);
      setUser(authRes.data.user);
    } catch (err) {
      console.error("Login failed:", err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [publicKey, signMessage]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    disconnect().catch(console.error);
  }, [disconnect]);

  return (
    <AuthContext.Provider
      value={{ user, token, isAuthenticated, isLoading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
