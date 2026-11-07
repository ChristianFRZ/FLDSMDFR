import { useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getRefreshToken, hasSession, onSessionEnded, setSession, type Tokens } from "../api/client";
import type { User } from "../api/types";

type Auth = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queries = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(hasSession());

  useEffect(() => {
    if (hasSession()) {
      api<User>("/api/users/me")
        .then(setUser)
        .catch(() => setUser(null))
        .finally(() => setLoading(false));
    }
    return onSessionEnded(() => {
      setUser(null);
      queries.clear();
    });
  }, [queries]);

  const enter = useCallback(async (tokens: Tokens) => {
    setSession(tokens);
    setUser(await api<User>("/api/users/me"));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await enter(await api<Tokens>("/api/auth/login", { method: "POST", json: { email, password } }));
    },
    [enter],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const json = { email, password, display_name: displayName };
      await enter(await api<Tokens>("/api/auth/register", { method: "POST", json }));
    },
    [enter],
  );

  const logout = useCallback(async () => {
    const refresh_token = getRefreshToken();
    if (refresh_token) {
      await api("/api/auth/logout", { method: "POST", json: { refresh_token } }).catch(() => undefined);
    }
    setSession(null);
    setUser(null);
    queries.clear();
  }, [queries]);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth necesita AuthProvider");
  return auth;
}
