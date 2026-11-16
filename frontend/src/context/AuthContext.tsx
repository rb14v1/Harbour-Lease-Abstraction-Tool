import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient, clearTokens, getAccessToken, setTokens } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    try {
      const response = await apiClient.get<User>("/auth/me/");
      setUser(response.data);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    const response = await apiClient.post("/auth/login/", { email, password });
    setTokens(response.data.access, response.data.refresh);
    const me = await apiClient.get<User>("/auth/me/");
    setUser(me.data);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
