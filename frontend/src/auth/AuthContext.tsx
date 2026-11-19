import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as cognito from "./cognito";

interface AuthState {
  status: "loading" | "authenticated" | "anonymous";
  user: { email: string; sub: string; name?: string } | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  /** Tokens vigentes (se renuevan solos). Lanza si la sesión expiró. */
  getTokens: () => Promise<{ idToken: string; accessToken: string }>;
}

const AuthContext = createContext<AuthState | null>(null);

export const SESSION_EXPIRED_EVENT = "tripplanner:session-expired";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [user, setUser] = useState<AuthState["user"]>(null);

  useEffect(() => {
    cognito.currentSession().then((s) => {
      if (s) {
        setUser({ email: s.email, sub: s.sub, name: s.name });
        setStatus("authenticated");
      } else setStatus("anonymous");
    });
  }, []);

  const signOut = useCallback(() => {
    cognito.signOut();
    setUser(null);
    setStatus("anonymous");
  }, []);

  // Cualquier 401 del backend cierra la sesión y lleva al login.
  useEffect(() => {
    const handler = () => signOut();
    window.addEventListener(SESSION_EXPIRED_EVENT, handler);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handler);
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const s = await cognito.signIn(email, password);
    setUser({ email: s.email, sub: s.sub, name: s.name });
    setStatus("authenticated");
  }, []);

  const getTokens = useCallback(async () => {
    const s = await cognito.currentSession();
    if (!s) {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      throw new Error("Sesión expirada");
    }
    return { idToken: s.idToken, accessToken: s.accessToken };
  }, []);

  const value = useMemo(
    () => ({ status, user, signIn, signOut, getTokens }),
    [status, user, signIn, signOut, getTokens],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
