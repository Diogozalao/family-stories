import { Loader2 } from "lucide-react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "../../store/auth";

/**
 * Gate for routes that require an authenticated user.
 *
 * Waits for the initial Supabase session hydration (``hydrating``) so
 * pages don't flicker to ``/login`` on hard refresh while the saved
 * session is still being read from localStorage.
 */
export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const token     = useAuthStore((s) => s.token);
  const hydrating = useAuthStore((s) => s.hydrating);
  const location  = useLocation();

  if (hydrating) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-stone-500" />
      </div>
    );
  }

  if (!token) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}
