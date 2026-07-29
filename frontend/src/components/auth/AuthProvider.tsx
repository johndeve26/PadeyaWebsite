"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ensureAccessTokenFresh,
  fetchMe,
  loginRequest,
  logoutRequest,
  refreshTokens,
  registerRequest,
  startImpersonationRequest,
  endImpersonationRequest,
} from "@/lib/api";
import { getOrCreateDeviceId } from "@/lib/auth/session-meta";
import { SESSION_EXPIRED_EVENT } from "@/lib/auth/session-expired";
import {
  clearImpersonationStash,
  clearTokens,
  getRefreshToken,
  hasStoredSession,
  isImpersonationSession,
  recordAuthLogin,
  restoreAdminTokens,
  setImpersonationAccessToken,
  setTokens,
  stashAdminTokens,
} from "@/lib/auth/storage";
import type {
  ImpersonationInfo,
  ImpersonationStartInput,
  User,
} from "@/lib/auth/types";

type AuthContextValue = {
  user: User | null;
  /** True until the first session bootstrap attempt finishes. */
  loading: boolean;
  /** Same as `!loading` — use before showing logged-out chrome. */
  authInitialized: boolean;
  impersonation: ImpersonationInfo | null;
  isImpersonating: boolean;
  login: (login: string, password: string) => Promise<User>;
  register: (input: {
    email: string;
    password: string;
    username: string;
    gender: string;
  }) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  startImpersonation: (input: ImpersonationStartInput) => Promise<string>;
  /** Ends impersonation and returns the admin return path (e.g. /admin/users/{id}). */
  stopImpersonation: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadUserAfterSessionReady(): Promise<User | null> {
  if (!hasStoredSession()) {
    return null;
  }
  if (isImpersonationSession()) {
    try {
      return await fetchMe();
    } catch {
      const restored = restoreAdminTokens();
      if (!restored) {
        clearTokens();
        clearImpersonationStash();
        return null;
      }
      try {
        return await fetchMe();
      } catch {
        clearTokens();
        clearImpersonationStash();
        return null;
      }
    }
  }

  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    return null;
  }

  const sessionOk = await ensureAccessTokenFresh();
  if (!sessionOk) {
    return null;
  }

  try {
    return await fetchMe();
  } catch {
    const tokens = await refreshTokens();
    if (!tokens) {
      return null;
    }
    try {
      return await fetchMe();
    } catch {
      return null;
    }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const me = await loadUserAfterSessionReady();
    setUser(me);
  }, []);

  useEffect(() => {
    let active = true;
    getOrCreateDeviceId();
    (async () => {
      try {
        const me = await loadUserAfterSessionReady();
        if (active) setUser(me);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // When API refresh fails, tokens are cleared but React `user` used to stay set —
  // unread/message polls then hammer /messages/unread-count with 401 forever.
  useEffect(() => {
    const onSessionExpired = () => {
      clearImpersonationStash();
      setUser(null);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => {
      window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    };
  }, []);

  const login = useCallback(async (login: string, password: string) => {
    clearImpersonationStash();
    const tokens = await loginRequest({ login, password });
    setTokens(tokens);
    recordAuthLogin();
    getOrCreateDeviceId();
    const me = await fetchMe();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(
    async (input: {
      email: string;
      password: string;
      username: string;
      gender: string;
    }) => {
      clearImpersonationStash();
      const tokens = await registerRequest(input);
      setTokens(tokens);
      recordAuthLogin();
      getOrCreateDeviceId();
      const me = await fetchMe();
      setUser(me);
      return me;
    },
    [],
  );

  const logout = useCallback(async () => {
    if (isImpersonationSession()) {
      try {
        await endImpersonationRequest();
      } catch {
        // Still leave the impersonation session locally.
      }
      clearTokens();
      clearImpersonationStash();
      setUser(null);
      return;
    }
    try {
      await logoutRequest();
    } finally {
      clearTokens();
      clearImpersonationStash();
      setUser(null);
    }
  }, []);

  const startImpersonation = useCallback(async (input: ImpersonationStartInput) => {
    if (isImpersonationSession()) {
      throw new Error("Already impersonating");
    }
    const result = await startImpersonationRequest({
      user_id: input.userId,
      reason: input.reason,
      support_ticket_id: input.supportTicketId,
      duration_minutes: input.durationMinutes ?? 30,
    });
    stashAdminTokens();
    setImpersonationAccessToken(result.access_token);
    const me = await fetchMe();
    setUser(me);
    return result.redirect_to;
  }, []);

  const stopImpersonation = useCallback(async (): Promise<string | null> => {
    if (!isImpersonationSession()) return null;
    const fallbackReturnTo = user?.impersonation?.target_user_id
      ? `/admin/users/${user.impersonation.target_user_id}`
      : user?.id
        ? `/admin/users/${user.id}`
        : "/admin/users";
    let returnTo = fallbackReturnTo;
    try {
      const ended = await endImpersonationRequest();
      if (ended.return_to) returnTo = ended.return_to;
    } catch {
      // Restore admin session even if end audit fails (e.g. expired token).
    }
    const restored = restoreAdminTokens();
    if (!restored) {
      clearTokens();
      clearImpersonationStash();
      setUser(null);
      return returnTo;
    }
    const me = await loadUserAfterSessionReady();
    setUser(me);
    return returnTo;
  }, [user]);

  const impersonation = user?.impersonation?.active ? user.impersonation : null;

  const value = useMemo(
    () => ({
      user,
      loading,
      authInitialized: !loading,
      impersonation,
      isImpersonating: Boolean(impersonation) || isImpersonationSession(),
      login,
      register,
      logout,
      refreshUser,
      startImpersonation,
      stopImpersonation,
    }),
    [
      user,
      loading,
      impersonation,
      login,
      register,
      logout,
      refreshUser,
      startImpersonation,
      stopImpersonation,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
