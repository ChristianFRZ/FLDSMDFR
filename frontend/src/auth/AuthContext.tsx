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
  /** `true` tras un login o registro correctos (no al recuperar una sesión guardada): toca la animación de entrada. */
  entered: boolean;
  clearEntered: () => void;
};

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queries = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(hasSession());
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    if (hasSession()) {
      api<User>("/api/users/me")
        .then(setUser)
        .catch(() => setUser(null))
        .finally(() => setLoading(false));
    }
    return onSessionEnded(() => {
      setUser(null);
      setEntered(false);
      queries.clear();
    });
  }, [queries]);

  const enter = useCallback(async (tokens: Tokens) => {
    setSession(tokens);
    setUser(await api<User>("/api/users/me"));
    setEntered(true);
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
    setEntered(false);
    queries.clear();
  }, [queries]);

  const clearEntered = useCallback(() => setEntered(false), []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, entered, clearEntered }),
    [user, loading, login, register, logout, entered, clearEntered],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth necesita AuthProvider");
  return auth;
}
