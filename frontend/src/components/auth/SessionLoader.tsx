import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { supabase } from "../../lib/supabase";
import { useAuthStore } from "../../store/auth";

/**
 * Wires Supabase auth state into the Zustand store and TanStack Query cache.
 *
 * Mounted once at the root of the app. On mount it hydrates the store
 * from whatever session Supabase has persisted in localStorage, then
 * subscribes to ``onAuthStateChange`` so subsequent sign-ins, sign-outs
 * and silent token refreshes keep the store (and the bearer token used
 * by ``api.ts``) up to date.
 */
export default function SessionLoader({ children }: { children: React.ReactNode }) {
  const setSession  = useAuthStore((s) => s.setSession);
  const setHydrated = useAuthStore((s) => s.setHydrated);
  const queryClient = useQueryClient();
  // The user id currently reflected in the cache. We only wipe the cache
  // when this actually changes — see the handler below.
  const currentUserId = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      currentUserId.current = data.session?.user?.id ?? null;
      setSession(data.session);
      setHydrated();
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      setSession(session);

      // Only drop the cache when the actual USER changes (signing in as a
      // different person, or signing out) — so we never show user A's data
      // to user B on the same tab.
      //
      // CRUCIAL: Supabase fires SIGNED_IN / USER_UPDATED on *routine token
      // refreshes* too (hourly, on tab re-focus, during long backend
      // operations). Wiping the cache on those events made the whole app
      // flash to "0 photos / 0 people / 0 stories" mid-session until a
      // manual page reload. Comparing the user id keeps refreshes silent.
      const nextUserId = session?.user?.id ?? null;
      if (nextUserId !== currentUserId.current) {
        currentUserId.current = nextUserId;
        queryClient.clear();
      }
    });

    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, [setSession, setHydrated, queryClient]);

  return <>{children}</>;
}
