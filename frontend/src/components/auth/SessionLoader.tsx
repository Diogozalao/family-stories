import { useEffect } from "react";
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

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setHydrated();
    });

    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (!active) return;
      setSession(session);

      // Drop every cached server response when the identity changes so
      // we never show user A's photos to user B who just signed in on
      // the same tab.
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
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
