import axios, { AxiosError } from "axios";

import { useAuthStore } from "../store/auth";
import { supabase } from "./supabase";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_BASE ??
  "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Read the bearer token straight out of the Zustand auth store
// (synchronous, ~µs). The Supabase ``onAuthStateChange`` listener
// installed by ``SessionLoader`` keeps this token fresh — including
// silent refreshes — so we never have to ``await`` Supabase on the
// request hot path.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    if (err.response?.status === 401) {
      // Token rejected by the backend — sign out so the UI redirects
      // to /login cleanly instead of looping on stale credentials.
      await supabase.auth.signOut();
    }
    return Promise.reject(err);
  },
);

/**
 * Build a fully-qualified URL for a photo or video served by the backend.
 *
 * The backend now 302-redirects to a Supabase Storage signed URL, so we
 * just need to attach the bearer token as a ``?token=`` query parameter
 * (the endpoints accept that fallback for ``<img>``/``<video>`` tags).
 */
export function mediaUrl(path: string): string {
  const token = useAuthStore.getState().token ?? "";
  const sep = path.includes("?") ? "&" : "?";
  return `${API_BASE}${path}${sep}token=${encodeURIComponent(token)}`;
}

/**
 * True when an axios error never received an HTTP response — i.e. the
 * connection dropped, timed out, or the response was lost (classic on a
 * free-tier backend waking from sleep). In these cases the request may
 * still have reached the server and committed, so callers should verify
 * by refetching rather than assuming outright failure.
 */
export function isLostResponse(err: unknown): boolean {
  return axios.isAxiosError(err) && !err.response;
}

/**
 * Ping the backend until it answers, so a cold-started free-tier server is
 * awake *before* we send a heavy, non-idempotent request (a file upload).
 *
 * The "Network Error on the first try, works after a page reload" symptom is
 * exactly this: Render spins the instance down when idle, and the very first
 * request that hits a sleeping server is dropped mid-flight while it boots
 * (~30–60 s). Reloading "fixed" it only because that failed request had
 * already woken the server. Pinging the public ``/healthz`` first absorbs the
 * boot delay on a cheap, idempotent GET, so the real upload then lands on an
 * awake server and succeeds on the first attempt.
 *
 * Resolves as soon as any HTTP response comes back (even an error status means
 * the server is up). Gives up quietly after ``maxWaitMs`` so the caller can
 * still attempt the request — the existing lost-response recovery remains a
 * second safety net.
 */
export async function wakeBackend(maxWaitMs = 75_000): Promise<void> {
  const deadline = Date.now() + maxWaitMs;
  while (Date.now() < deadline) {
    try {
      // Bare axios (no interceptors/auth) — a 401 here must not trip the
      // global sign-out path, and the health probe needs no token.
      await axios.get(`${API_BASE}/healthz`, { timeout: 8000 });
      return;                                  // 2xx → awake
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) return;   // any status → awake
      await new Promise((r) => setTimeout(r, 3000));         // no response → still booting
    }
  }
}

/**
 * Download the family tree as a GEDCOM (.ged) file. Goes through the axios
 * instance so the auth token is attached, then triggers a browser download.
 */
export async function downloadGedcom(familyLabel?: string | null): Promise<void> {
  const res = await api.get("/api/v1/genealogy/export/gedcom", {
    params: familyLabel ? { family_label: familyLabel } : {},
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(familyLabel || "familia").replace(/\s+/g, "_")}.ged`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function extractErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length && typeof detail[0] === "object") {
      return (detail[0] as { msg?: string }).msg ?? fallback;
    }
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
