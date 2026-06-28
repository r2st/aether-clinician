'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, tokenStore } from './api';
import type { Account } from './types';

interface AuthState {
  account: Account | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  account: null,
  loading: true,
  refresh: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!tokenStore.access) {
      setAccount(null);
      setLoading(false);
      return;
    }
    try {
      setAccount(await api.me());
    } catch {
      setAccount(null);
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    await api.logout();
    setAccount(null);
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <AuthContext.Provider value={{ account, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

/** Redirect to /login when there is no authenticated account. */
export function useRequireAuth() {
  const { account, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !account) router.replace('/login');
  }, [account, loading, router]);
  return { account, loading };
}
