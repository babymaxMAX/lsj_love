"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authExchangeToken, authMe } from "@/lib/api";

interface AuthContextValue {
  userId: string | null;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  userId: null,
  loading: true,
  error: null,
  clearError: () => {},
});

export function useCurrentUser() {
  const ctx = useContext(AuthContext);
  return ctx.userId;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  const clearError = () => setError(null);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const token = searchParams.get("token");
        if (token) {
          try {
            const data = await authExchangeToken(token);
            if (cancelled) return;
            if (data.ok && data.telegram_id) {
              setUserId(String(data.telegram_id));
              setLoading(false);
              router.replace("/app");
              return;
            }
          } catch (e) {
            if (!cancelled) {
              setError(String(e));
              setLoading(false);
            }
            return;
          }
        }
        const me = await authMe();
        if (cancelled) return;
        if (me?.telegram_id) {
          setUserId(String(me.telegram_id));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [searchParams, router]);

  return (
    <AuthContext.Provider value={{ userId, loading, error, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}
