import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE, isLostResponse, wakeBackend } from "./api";
import { supabase } from "./supabase";
import type {
  FamilyTreeData, HealthCheck, MediaFile, NarrativeTemplate, Person, Project, Story,
  TaskRecord, TimelineEvent, Video,
} from "./types";

interface PersonInput {
  name: string;
  sex?: string | null;
  birth_date?: string | null;
  death_date?: string | null;
  birth_place?: string | null;
  notes?: string | null;
  family_label?: string | null;
  photo_media_id?: number | null;
  project_id?: number | null;
}
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
  // The backend wipes every owned row AND deletes the Supabase Auth user via
  // the admin API, so the credentials actually stop working (the old version
  // only signed out, which is why a "deleted" account could still log in).
  // Afterwards we clear the local session so the UI returns to the landing.
  return useMutation({
    mutationFn: async (_input?: { current_password?: string; confirm?: string }) => {
      await api.delete("/api/v1/auth/account");
      await supabase.auth.signOut();
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
    // While any photo is still being analysed in the background (M1 defers
    // the slow Gemini/OCR step), poll so the description/status fill in on
    // their own. Stops polling once everything is settled.
    refetchInterval: (query) => {
      const data = query.state.data as MediaFile[] | undefined;
      const pending = data?.some(
        (m) => m.status === "processing" || m.status === "pending",
      );
      return pending ? 4000 : false;
    },
  });
}

export function useDeletePhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/media/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["media"] }),
  });
}

export function useSetMediaPersons() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: number; person_ids: number[] }) =>
      (await api.put(`/api/v1/media/${input.id}/persons`, { person_ids: input.person_ids })).data as MediaFile,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["media"] });
      // Project photo/timeline tabs read project-scoped media — refresh them too.
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useUpdateMedia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: number; date_taken?: string | null; location_name?: string }) => {
      const { id, ...body } = input;
      return (await api.patch(`/api/v1/media/${id}`, body)).data as MediaFile;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["media"] });
      qc.invalidateQueries({ queryKey: ["timeline"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useUploadPhoto() {
  const qc = useQueryClient();
  return useMutation({
    // ``projectId`` uploads the photo straight into a project (isolated from
    // the Library); omitted = global Library.
    mutationFn: async (input: File | { file: File; projectId?: number | null; analyze?: boolean }) => {
      const file = input instanceof File ? input : input.file;
      const projectId = input instanceof File ? undefined : input.projectId;
      // ``analyze: false`` skips Gemini Vision (profile portraits) to save quota.
      const analyze = input instanceof File ? undefined : input.analyze;
      await wakeBackend();           // absorb cold-start before the upload
      const form = new FormData();
      form.append("file", file);
      if (projectId != null) form.append("project_id", String(projectId));
      if (analyze === false) form.append("analyze", "false");
      const { data } = await api.post("/api/v1/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["media"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

/** Re-run the AI vision on photos that have no description yet (e.g. ones
 *  analysed while the Gemini key was down). Marks them COMPLETED, which also
 *  unblocks video generation. Long request (one Gemini call per photo). */
export function useReanalyzePhotos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await api.post("/api/v1/narrative/reanalyze-photos")).data as {
        photos_considered: number; described: number; still_missing: number;
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
    // Photos uploaded into a project are analysed in the background (same as
    // the Library). Poll while any is still processing so the AI description
    // shows up on its own — otherwise the project view looked "not analysed".
    refetchInterval: (query) => {
      const data = query.state.data as MediaFile[] | undefined;
      const pending = data?.some((m) => m.status === "processing" || m.status === "pending");
      return pending ? 4000 : false;
    },
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
export function usePersons(projectId?: number | null) {
  return useQuery<Person[]>({
    // ``projectId`` scopes to that project's isolated family; omitted = the
    // global Family (people with no project).
    queryKey: ["persons", projectId ?? "global"],
    queryFn: async () => {
      try {
        const params = projectId != null ? { params: { project_id: projectId } } : {};
        return (await api.get("/api/v1/genealogy/persons", params)).data;
      } catch {
        return [];
      }
    },
  });
}

export function useUploadGedcom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { file: File; familyLabel?: string; projectId?: number | null }) => {
      // Make sure the (possibly cold-started) backend is awake before we send
      // the multipart import — otherwise the first request is dropped while
      // the server boots and surfaces as a "Network Error" that only a page
      // reload seemed to fix. See ``wakeBackend``.
      await wakeBackend();
      const form = new FormData();
      form.append("file", input.file);
      if (input.familyLabel) form.append("family_label", input.familyLabel);
      if (input.projectId != null) form.append("project_id", String(input.projectId));
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

export function useFamilies(projectId?: number | null) {
  return useQuery<{ label: string | null; count: number }[]>({
    queryKey: ["families", projectId ?? "global"],
    queryFn: async () => {
      const params = projectId != null ? { params: { project_id: projectId } } : {};
      return (await api.get("/api/v1/genealogy/families", params)).data;
    },
  });
}

export function useClearFamily() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input?: { familyLabel?: string; projectId?: number | null }) => {
      const params: Record<string, unknown> = {};
      if (input?.familyLabel) params.family_label = input.familyLabel;
      if (input?.projectId != null) params.project_id = input.projectId;
      const { data } = await api.delete("/api/v1/genealogy/persons", { params });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["persons"] });
      qc.invalidateQueries({ queryKey: ["families"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
      qc.invalidateQueries({ queryKey: ["tree"] });
    },
  });
}

// ── Family tree (DB-backed persons + relationships) ───────────────────────
export function useFamilyTree(familyLabel?: string | null, projectId?: number | null) {
  return useQuery<FamilyTreeData>({
    // ``projectId`` scopes to a project; ``familyLabel`` filters to one
    // sub-family within the scope.
    queryKey: ["tree", projectId ?? "global", familyLabel ?? null],
    queryFn: async () => {
      const params: Record<string, unknown> = {};
      if (projectId != null) params.project_id = projectId;
      if (familyLabel) params.family_label = familyLabel;
      return (await api.get("/api/v1/genealogy/tree", { params })).data;
    },
  });
}

function useTreeInvalidator() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["tree"] });
    qc.invalidateQueries({ queryKey: ["persons"] });
    qc.invalidateQueries({ queryKey: ["families"] });
    qc.invalidateQueries({ queryKey: ["graph"] });
  };
}

export function useCreatePerson() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (input: PersonInput) =>
      (await api.post("/api/v1/genealogy/persons", input)).data as Person,
    onSuccess: invalidate,
  });
}

export function useUpdatePerson() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (input: { id: number } & Partial<PersonInput>) => {
      const { id, ...body } = input;
      return (await api.patch(`/api/v1/genealogy/persons/${id}`, body)).data as Person;
    },
    onSuccess: invalidate,
  });
}

export function useDeletePerson() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/genealogy/persons/${id}`)).data,
    onSuccess: invalidate,
  });
}

export function useCreateRelationship() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (input: { from_person_id: number; to_person_id: number; kind: string }) =>
      (await api.post("/api/v1/genealogy/relationships", input)).data,
    onSuccess: invalidate,
  });
}

export function useDeleteRelationship() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/api/v1/genealogy/relationships/${id}`)).data,
    onSuccess: invalidate,
  });
}

export interface BulkPersonInput {
  ref: string;
  name: string;
  sex?: string | null;
  birth_date?: string | null;
  family_label?: string | null;
}
export interface BulkRelInput { from_ref: string; to_ref: string; kind: string }

export function useSaveTreePositions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { positions: { id: number; x: number | null; y: number | null }[] }) =>
      (await api.post("/api/v1/genealogy/tree/positions", input)).data,
    // Refresh the cached tree so the saved position survives leaving and
    // coming back to the view (the node is already where it was dropped,
    // so this doesn't cause a visible jump).
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tree"] }),
  });
}

export function useBulkTree() {
  const invalidate = useTreeInvalidator();
  return useMutation({
    mutationFn: async (input: { persons: BulkPersonInput[]; relationships: BulkRelInput[] }) =>
      (await api.post("/api/v1/genealogy/tree/bulk", input)).data,
    onSuccess: invalidate,
  });
}

// ── Timeline ────────────────────────────────────────────────────────────
export function useTimeline(projectId?: number | null) {
  return useQuery<TimelineEvent[]>({
    // ``projectId`` scopes to a project's own events (e.g. GEDCOM marriages /
    // births imported into it); omitted = the global timeline.
    queryKey: ["timeline", projectId ?? "global"],
    queryFn: async () => {
      try {
        const params = projectId != null ? { params: { project_id: projectId } } : {};
        return (await api.get("/api/v1/timeline", params)).data;
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
    retry: (count, err) => isLostResponse(err) && count < 4,
    retryDelay: (count) => Math.min(2000 * (count + 1), 8000),
  });
}

export function useStory(id: number | null) {
  return useQuery<Story>({
    queryKey: ["stories", id],
    queryFn: async () => (await api.get(`/api/v1/narrative/stories/${id}`)).data,
    enabled: id !== null,
    // A lost response (cold start) is worth retrying a few times with a
    // growing delay, so the page recovers on its own instead of dead-ending.
    retry: (count, err) => isLostResponse(err) && count < 4,
    retryDelay: (count) => Math.min(2000 * (count + 1), 8000),
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
  /** Optional explicit photo selection — empty means "use every photo". */
  media_ids?: number[];
  project_id?: number | null;
  custom_tone?: string;
  custom_structure?: string;
  /** Two-letter language code — defaults to the active i18n locale on the
   *  caller side. Stored on the Story so the M4 TTS later picks the
   *  matching voice (e.g. ``pt-PT-DuarteNeural`` vs ``en-GB-RyanNeural``). */
  language?: string;
  /** Narrator voice for the documentary: "male" or "female". */
  voice?: string;
  /** Include a narration subtitle track (default true). */
  subtitles?: boolean;
  /** Subtitle size in the player: "small" | "medium" | "large". */
  subtitle_size?: string;
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
    mutationFn: async (input: { id: number; title?: string; narrative?: string; favorite?: boolean }) => {
      const { id, ...body } = input;
      return (await api.patch(`/api/v1/narrative/stories/${id}`, body)).data as Story;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["stories"] });
      qc.invalidateQueries({ queryKey: ["stories", vars.id] });
    },
  });
}

/** Rewrite a story's narrative in place, steered by free-text feedback. */
export function useRegenerateStory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: number; feedback: string }) =>
      (await api.post(`/api/v1/narrative/stories/${input.id}/regenerate`,
        { feedback: input.feedback })).data as Story,
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
    // A synchronous render can outlive the HTTP request on the free tier
    // (proxy timeout). Keep polling while any video is still "processing"
    // so the finished MP4 shows up on its own once the server commits it,
    // even if the original request already gave up.
    refetchInterval: (query) => {
      const data = query.state.data as Video[] | undefined;
      return data?.some((v) => v.status === "processing") ? 5000 : false;
    },
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

export function useDeleteVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete(`/api/v1/multimedia/videos/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["videos"] }),
  });
}

export function videoUrl(filename: string): string {
  const token = useAuthStore.getState().token;
  const base  = `${API_BASE}/api/v1/multimedia/video/${encodeURIComponent(filename)}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

/** Like ``videoUrl`` but forces the browser to SAVE the file (the signed URL
 *  gets a ``download`` flag) instead of opening it. */
export function downloadVideoUrl(filename: string): string {
  const token = useAuthStore.getState().token;
  const base  = `${API_BASE}/api/v1/multimedia/video/${encodeURIComponent(filename)}?download=1`;
  return token ? `${base}&token=${encodeURIComponent(token)}` : base;
}

// ── Tasks ───────────────────────────────────────────────────────────────
export function useTasks(projectId?: number) {
  const qs = projectId != null ? `&project_id=${projectId}` : "";
  return useQuery<TaskRecord[]>({
    queryKey: ["tasks", projectId ?? null],
    queryFn: async () => (await api.get(`/api/v1/tasks?limit=50${qs}`)).data,
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

