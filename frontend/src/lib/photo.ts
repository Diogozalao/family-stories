import { API_BASE } from "./api";

/** Build a URL that serves the photo bytes from the backend (used by <img>). */
export function photoUrl(mediaId: number): string {
  return `${API_BASE}/api/v1/media/${mediaId}/file`;
}
