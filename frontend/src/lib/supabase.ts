import { createClient } from "@supabase/supabase-js";

const url     = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Caught at import time — the rest of the app cannot meaningfully run
  // without these. Fail loud and early in dev so we don't ship a build
  // that silently breaks login.
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY in frontend/.env",
  );
}

// One module-level instance so every component shares the same session
// state and the auth listener fires exactly once per change.
export const supabase = createClient(url, anonKey, {
  auth: {
    persistSession:    true,
    autoRefreshToken:  true,
    detectSessionInUrl: true,    // Handles the "#access_token=..." fragment on reset/confirm.
  },
});
