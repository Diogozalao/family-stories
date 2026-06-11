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
