"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import * as api from "./api";
import { getStoredToken, setStoredToken } from "./api";
import type { UserRead } from "./types";

interface AuthContextValue {
  user: UserRead | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = getStoredToken();
    const hydration = storedToken
      ? api
          .getCurrentUser()
          .then((fetchedUser) => {
            setToken(storedToken);
            setUser(fetchedUser);
          })
          .catch(() => {
            // Stored token is no longer valid (expired/revoked) — clear it.
            setStoredToken(null);
          })
      : Promise.resolve();

    hydration.finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const response = await api.login(username, password);
    setStoredToken(response.token);
    setToken(response.token);
    setUser(response.user);
  }, []);

  const logout = useCallback(() => {
    api.logout().catch(() => {
      // Session may already be invalid server-side — clear local state anyway.
    });
    setStoredToken(null);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
