import type { Session } from "@supabase/supabase-js";
import { create } from "zustand";

/**
 * Auth identity cache backed by Supabase.
 *
 * Supabase already persists the session in localStorage for us — this
 * store is just a reactive mirror so React components can subscribe to
 * "is the user logged in?" without each one calling
 * ``supabase.auth.getSession()`` on every render. The hydration happens
 * in :file:`components/auth/SessionLoader.tsx`.
 */
export interface User {
  id:    string;       // Supabase ``auth.users.id`` UUID.
  email: string | null;
  /** Display name from ``user_metadata.username``, set at signup. May
   *  be ``null`` for accounts created before this field existed. */
  username: string | null;
}

interface AuthState {
  /** Bearer token from the active Supabase session, or null when signed out. */
  token: string | null;
  user:  User   | null;
  /** True until the first ``getSession`` call resolves — guards UI from flashing
   *  the "logged out" state for users who actually had a saved session. */
  hydrating: boolean;
  setSession: (session: Session | null) => void;
  setHydrated: () => void;
}

function userFromSession(session: Session | null): User | null {
  if (!session?.user) return null;
  const meta = (session.user.user_metadata ?? {}) as { username?: string };
  return {
    id:       session.user.id,
    email:    session.user.email ?? null,
    username: meta.username ?? null,
  };
}

export const useAuthStore = create<AuthState>()((set) => ({
  token:     null,
  user:      null,
  hydrating: true,
  setSession: (session) => set({
    token: session?.access_token ?? null,
    user:  userFromSession(session),
  }),
  setHydrated: () => set({ hydrating: false }),
}));
