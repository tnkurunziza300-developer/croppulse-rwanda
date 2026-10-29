import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, ApiError, deleteAccount as deleteAccountRequest, exchangeReactHandoff, initializeCsrf, registerAccount, signIn, signOut } from './api';
import type { Farmer } from './api';

interface AuthValue {
  user: Farmer | null;
  ready: boolean;
  error: string;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string, name: string, privacyAccepted: boolean): Promise<void>;
  logout(): Promise<void>;
  deleteAccount(password: string): Promise<void>;
  clearLocalSession(): void;
}
const AuthContext = createContext<AuthValue | null>(null);
let authBootstrapPromise: Promise<Farmer | null> | null = null;

function bootstrapBrowserSession(): Promise<Farmer | null> {
  if (authBootstrapPromise) return authBootstrapPromise;
  const pending = (async () => {
    const url = new URL(window.location.href);
    const handoffCode = url.searchParams.get('cp_handoff');
    if (handoffCode) {
      url.searchParams.delete('cp_handoff');
      window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
    }
    await initializeCsrf();
    if (handoffCode) return exchangeReactHandoff(handoffCode);
    try { return await api<Farmer>('/v1/me'); }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) return null;
      throw err;
    }
  })();
  authBootstrapPromise = pending;
  return pending.finally(() => {
    if (authBootstrapPromise === pending) authBootstrapPromise = null;
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Farmer | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        setUser(await bootstrapBrowserSession());
      } catch (err) {
        if (mounted && err instanceof Error) setError(err.message);
      } finally {
        if (mounted) setReady(true);
      }
    })();
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const handleExpiredSession = () => {
      setUser(null);
      setError('Your session ended. Sign in again to continue.');
    };
    window.addEventListener('croppulse:session-expired', handleExpiredSession);
    return () => window.removeEventListener('croppulse:session-expired', handleExpiredSession);
  }, []);

  const value = useMemo<AuthValue>(() => ({
    user, ready, error,
    async login(email, password) { setError(''); setUser(await signIn(email, password)); },
    async register(email, password, name, privacyAccepted) { setError(''); setUser(await registerAccount(email, password, name, privacyAccepted)); },
    async logout() {
      setError('');
      try { await signOut(); setUser(null); }
      catch (err) {
        if (err instanceof ApiError && err.status === 401) setUser(null);
        else setError(err instanceof Error ? `${err.message} Sign-out was not confirmed; the server session may remain active.` : 'Sign-out was not confirmed; the server session may remain active.');
      }
    },
    async deleteAccount(password) {
      await deleteAccountRequest(password);
      setUser(null);
      setError('');
    },
    clearLocalSession() { setUser(null); setError(''); },
  }), [user, ready, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
