import { API_BASE } from "./api";
import { useAuthStore } from "../store/auth";

/** Build a URL that serves the photo bytes from the backend.
 *
 * Appends the current JWT as a query param so the browser's ``<img>``
 * tag (which can't set headers) still authenticates against the
 * protected endpoint.
 */
export function photoUrl(mediaId: number): string {
  const token = useAuthStore.getState().token;
  const base  = `${API_BASE}/api/v1/media/${mediaId}/file`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}
