import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE } from "./api";
import { supabase } from "./supabase";
import type {
  HealthCheck, MediaFile, NarrativeTemplate, Person, Project, Story,
  TaskRecord, TimelineEvent, Video,
} from "./types";
import { useAuthStore } from "../store/auth";

// ── Auth ────────────────────────────────────────────────────────────────
//
// Every flow below delegates to ``supabase.auth.*``. The Zustand store
// is kept in sync by the ``SessionLoader`` listener — none of these
// hooks have to write to the store themselves.

export function useLogin() {
  return useMutation({
    mutationFn: async (input: { username: string; password: string }) => {
      const { data, error } = await supabase.auth.signInWithPassword({
        email:    input.username,
        password: input.password,
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (input: { email: string; password: string; username?: string }) => {
      const { data, error } = await supabase.auth.signUp({
        email:    input.email,
        password: input.password,
        options:  {
          // ``user_metadata`` is the only Supabase field for arbitrary
          // signup-time data — we store the display name here so the UI
          // can show "Diogo" instead of the email on every page.
          data: { username: input.username?.trim() || undefined },
        },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useChangePassword() {
  // Supabase doesn't natively re-verify the current password before
  // updating — the active session is treated as proof of identity. We
  // therefore ignore ``current_password`` for now to stay compatible
  // with the existing UI; tighten this later if it matters.
  return useMutation({
    mutationFn: async (input: { current_password?: string; new_password: string }) => {
      const { error } = await supabase.auth.updateUser({ password: input.new_password });
      if (error) throw error;
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: async (input: { email: string }) => {
      const { error } = await supabase.auth.resetPasswordForEmail(input.email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (error) throw error;
    },
  });
}

export function useResetPassword() {
  // When the user lands on /reset-password via the email link, Supabase
  // has already turned the URL fragment into an active session — we just
  // call ``updateUser`` with the new password. The legacy ``token`` arg
  // is accepted but ignored so callers don't need to change shape yet.
  return useMutation({
    mutationFn: async (input: { token?: string; new_password: string }) => {
      const { error } = await supabase.auth.updateUser({ password: input.new_password });
      if (error) throw error;
    },
  });
}

export function useDeleteAccount() {
  // Implementação atual: simples sign-out + nota. Apagar a conta
  // requer permissões admin que ainda não expusemos via backend. Volta
  // a isto quando precisares mesmo (ver TODO em routes/auth.py).
  return useMutation({
    mutationFn: async (_input: { current_password: string; confirm: string }) => {
      await supabase.auth.signOut();
      throw new Error("A eliminação definitiva de conta ainda não está disponível — só sessão terminada.");
    },
  });
}

// ── Health ──────────────────────────────────────────────────────────────
export function useHealth() {
  return useQuery<HealthCheck>({
    queryKey: ["health"],
    queryFn: async () => (await api.get("/healthz")).data,
    refetchInterval: 30_000,
  });
}

// ── Media ───────────────────────────────────────────────────────────────
export function useMedia() {
  return useQuery<MediaFile[]>({
    queryKey: ["media"],
    queryFn: async () => (await api.get("/api/v1/media")).data,
  });
}

export function useDeletePhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/media/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["media"] }),
  });
}

export function useUploadPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/api/v1/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["media"] }),
  });
}

// ── Projects ────────────────────────────────────────────────────────────
export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: async () => (await api.get("/api/v1/projects")).data,
  });
}

export function useProject(id: number | null) {
  return useQuery<Project>({
    queryKey: ["projects", id],
    queryFn: async () => (await api.get(`/api/v1/projects/${id}`)).data,
    enabled: id !== null,
  });
}

export function useProjectMedia(id: number | null) {
  return useQuery<MediaFile[]>({
    queryKey: ["projects", id, "media"],
    queryFn: async () => (await api.get(`/api/v1/projects/${id}/media`)).data,
    enabled: id !== null,
  });
}

export function useProjectStories(id: number | null) {
  return useQuery<Story[]>({
    queryKey: ["projects", id, "stories"],
    queryFn: async () => (await api.get(`/api/v1/projects/${id}/stories`)).data,
    enabled: id !== null,
  });
}

export function useProjectVideos(id: number | null) {
  return useQuery<Video[]>({
    queryKey: ["projects", id, "videos"],
    queryFn: async () => (await api.get(`/api/v1/projects/${id}/videos`)).data,
    enabled: id !== null,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; description?: string }) =>
      (await api.post("/api/v1/projects", input)).data as Project,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/projects/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useAddMediaToProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { projectId: number; mediaIds: number[] }) =>
      (await api.post(`/api/v1/projects/${input.projectId}/media`, { media_ids: input.mediaIds })).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId, "media"] });
    },
  });
}

export function useRemoveMediaFromProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { projectId: number; mediaId: number }) =>
      (await api.delete(`/api/v1/projects/${input.projectId}/media/${input.mediaId}`)).data,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId, "media"] });
    },
  });
}

// ── Genealogy ───────────────────────────────────────────────────────────
export function usePersons() {
  return useQuery<Person[]>({
    queryKey: ["persons"],
    queryFn: async () => {
      try {
        return (await api.get("/api/v1/genealogy/persons")).data;
      } catch {
        return [];
      }
    },
  });
}

export function useUploadGedcom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { file: File; familyLabel?: string }) => {
      const form = new FormData();
      form.append("file", input.file);
      if (input.familyLabel) form.append("family_label", input.familyLabel);
      // 5-minute ceiling for very large trees — the backend usually finishes
      // in seconds with the session pooler, but the previous timeout (none)
      // surfaced confusing "Network Error" toasts when the browser itself
      // gave up first.
      const { data } = await api.post("/api/v1/genealogy/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300_000,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["persons"] });
      qc.invalidateQueries({ queryKey: ["families"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useFamilies() {
  return useQuery<{ label: string | null; count: number }[]>({
    queryKey: ["families"],
    queryFn: async () => (await api.get("/api/v1/genealogy/families")).data,
  });
}

export function useClearFamily() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (familyLabel?: string) => {
      const params = familyLabel ? { params: { family_label: familyLabel } } : {};
      const { data } = await api.delete("/api/v1/genealogy/persons", params);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["persons"] });
      qc.invalidateQueries({ queryKey: ["families"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

// ── Timeline ────────────────────────────────────────────────────────────
export function useTimeline() {
  return useQuery<TimelineEvent[]>({
    queryKey: ["timeline"],
    queryFn: async () => {
      try {
        return (await api.get("/api/v1/timeline")).data;
      } catch {
        return [];
      }
    },
  });
}

export function useBuildTimeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post("/api/v1/timeline/build")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeline"] }),
  });
}

// ── Narrative ───────────────────────────────────────────────────────────
export function useStories() {
  return useQuery<Story[]>({
    queryKey: ["stories"],
    queryFn: async () => (await api.get("/api/v1/narrative/stories")).data,
  });
}

export function useStory(id: number | null) {
  return useQuery<Story>({
    queryKey: ["stories", id],
    queryFn: async () => (await api.get(`/api/v1/narrative/stories/${id}`)).data,
    enabled: id !== null,
  });
}

export function useTemplates() {
  return useQuery<NarrativeTemplate[]>({
    queryKey: ["templates"],
    queryFn: async () => (await api.get("/api/v1/narrative/templates")).data,
    staleTime: Infinity,
  });
}

export function useIndexFacts() {
  return useMutation({
    mutationFn: async () => (await api.post("/api/v1/narrative/index")).data,
  });
}

export interface GenerateInput {
  title: string;
  event_type: string;
  query: string;
  person_ids: number[];
  project_id?: number | null;
  custom_tone?: string;
  custom_structure?: string;
  /** Two-letter language code — defaults to the active i18n locale on the
   *  caller side. Stored on the Story so the M4 TTS later picks the
   *  matching voice (e.g. ``pt-PT-DuarteNeural`` vs ``en-GB-RyanNeural``). */
  language?: string;
}

export function useGenerateNarrative() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: GenerateInput & { mode: "sync" | "background" }) => {
      const { mode, ...payload } = input;
      const { data } = await api.post(
        `/api/v1/narrative/generate?mode=${mode}`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stories"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useDeleteStory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/narrative/stories/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stories"] }),
  });
}

export function useUpdateStory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: number; title?: string; narrative?: string }) => {
      const { id, ...body } = input;
      return (await api.patch(`/api/v1/narrative/stories/${id}`, body)).data as Story;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["stories"] });
      qc.invalidateQueries({ queryKey: ["stories", vars.id] });
    },
  });
}

// ── Multimedia ──────────────────────────────────────────────────────────
export function useVideos() {
  return useQuery<Video[]>({
    queryKey: ["videos"],
    queryFn: async () => (await api.get("/api/v1/multimedia/videos")).data,
  });
}

export function useGenerateVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { story_id: number; mode: "sync" | "background" }) => {
      const { data } = await api.post(
        `/api/v1/multimedia/generate/${input.story_id}?mode=${input.mode}`,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["videos"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function videoUrl(filename: string): string {
  const token = useAuthStore.getState().token;
  const base  = `${API_BASE}/api/v1/multimedia/video/${encodeURIComponent(filename)}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

// ── Tasks ───────────────────────────────────────────────────────────────
export function useTasks() {
  return useQuery<TaskRecord[]>({
    queryKey: ["tasks"],
    queryFn: async () => (await api.get("/api/v1/tasks?limit=50")).data,
    refetchInterval: 3_000,
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post(`/api/v1/tasks/${id}/cancel`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete(`/api/v1/tasks/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useClearFinishedTasks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.delete("/api/v1/tasks")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

