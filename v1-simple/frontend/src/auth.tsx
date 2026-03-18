/**
 * auth.tsx — Unified auth abstraction
 *
 * In HTTPS (secure context): delegates to LogtoProvider via LogtoAuthBridge.
 * In HTTP (insecure context): provides mock auth so Crypto.subtle error is avoided.
 */
import React, { createContext, useContext } from 'react';
import { useLogto } from '@logto/react';

export interface AppAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (redirectUri?: string) => Promise<void>;
  signOut: (redirectUri?: string) => Promise<void>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getIdTokenClaims: () => Promise<Record<string, any> | undefined>;
}

const defaultState: AppAuthState = {
  isAuthenticated: false,
  isLoading: true,
  signIn: async () => {},
  signOut: async () => {},
  getIdTokenClaims: async () => undefined,
};

export const AppAuthContext = createContext<AppAuthState>(defaultState);

/** Use this everywhere instead of useLogto() */
export function useAppAuth(): AppAuthState {
  return useContext(AppAuthContext);
}

/**
 * LogtoAuthBridge — must be rendered inside <LogtoProvider>.
 * Reads Logto state and feeds it into AppAuthContext.
 */
export function LogtoAuthBridge({ children }: { children: React.ReactNode }) {
  const logto = useLogto();
  const value: AppAuthState = {
    isAuthenticated: logto.isAuthenticated,
    isLoading: logto.isLoading,
    signIn: logto.signIn as AppAuthState['signIn'],
    signOut: logto.signOut as AppAuthState['signOut'],
    getIdTokenClaims: logto.getIdTokenClaims as AppAuthState['getIdTokenClaims'],
  };
  return <AppAuthContext.Provider value={value}>{children}</AppAuthContext.Provider>;
}

/**
 * MockAuthProvider — used in HTTP / insecure contexts.
 * Auto-authenticates as a dev user; no Logto SDK touched.
 */
export function MockAuthProvider({ children }: { children: React.ReactNode }) {
  const value: AppAuthState = {
    isAuthenticated: true,
    isLoading: false,
    signIn: async () => {},
    signOut: async () => {
      window.location.href = window.location.origin;
    },
    getIdTokenClaims: async () => ({
      sub: 'dev',
      name: '开发模式 (HTTP)',
    }),
  };
  return <AppAuthContext.Provider value={value}>{children}</AppAuthContext.Provider>;
}
