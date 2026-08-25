/** Session state: the only place tokens and the current user are owned. */

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { authApi, setSessionExpiredHandler, tokenStore } from "../api/client";
import type { User } from "../api/types";

export interface AuthContextValue {
  user: User | null;
  status: "loading" | "authenticated" | "anonymous";
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");
  const queryClient = useQueryClient();

  // Restore the session on boot: a stored token is only trusted once /auth/me confirms it.
  useEffect(() => {
    let cancelled = false;

    if (!tokenStore.access()) {
      setStatus("anonymous");
      return;
    }

    authApi
      .me()
      .then((profile) => {
        if (cancelled) return;
        setUser(profile);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        tokenStore.clear();
        setStatus("anonymous");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // A refresh failure anywhere in the app lands here.
  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null);
      setStatus("anonymous");
      queryClient.clear();
    });
  }, [queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login(email, password);
      tokenStore.save(response);
      setUser(response.user);
      setStatus("authenticated");
      queryClient.clear();
    },
    [queryClient],
  );

  const register = useCallback(
    async (fullName: string, email: string, password: string) => {
      const response = await authApi.register(fullName, email, password);
      tokenStore.save(response);
      setUser(response.user);
      setStatus("authenticated");
      queryClient.clear();
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Already invalid server-side; the local session still has to go.
    } finally {
      tokenStore.clear();
      setUser(null);
      setStatus("anonymous");
      queryClient.clear();
    }
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout, setUser }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
