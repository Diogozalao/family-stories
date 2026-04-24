import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE } from "./api";
import type {
  HealthCheck, MediaFile, NarrativeTemplate, Person, Story, TaskRecord,
  TimelineEvent, Video,
} from "./types";
import { useAuthStore, type User } from "../store/auth";

// ── Auth ────────────────────────────────────────────────────────────────
export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  return useMutation({
    mutationFn: async (input: { username: string; password: string }) => {
      const form = new URLSearchParams();
      form.set("username", input.username);
      form.set("password", input.password);
      const { data } = await api.post("/api/v1/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return data as { access_token: string; user: User };
    },
    onSuccess: (data) => setAuth(data.access_token, data.user),
  });
}

export function useRegister() {
  const setAuth = useAuthStore((s) => s.setAuth);
  return useMutation({
    mutationFn: async (input: { username: string; password: string }) => {
      const { data } = await api.post("/api/v1/auth/register", input);
      return data as { access_token: string; user: User };
    },
    onSuccess: (data) => setAuth(data.access_token, data.user),
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
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/api/v1/genealogy/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["persons"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useFamilyGraph() {
  return useQuery<{ nodes: unknown[]; links: unknown[] }>({
    queryKey: ["graph"],
    queryFn: async () => {
      try {
        return (await api.get("/api/v1/genealogy/graph")).data;
      } catch {
        return { nodes: [], links: [] };
      }
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
  return `${API_BASE}/api/v1/multimedia/video/${encodeURIComponent(filename)}`;
}

// ── Tasks ───────────────────────────────────────────────────────────────
export function useTasks() {
  return useQuery<TaskRecord[]>({
    queryKey: ["tasks"],
    queryFn: async () => (await api.get("/api/v1/tasks?limit=50")).data,
    refetchInterval: 3_000,
  });
}

export function useTask(id: number | null) {
  return useQuery<TaskRecord>({
    queryKey: ["tasks", id],
    queryFn: async () => (await api.get(`/api/v1/tasks/${id}`)).data,
    enabled: id !== null,
    refetchInterval: (q) => {
      const s = q.state.data?.state;
      return s === "done" || s === "failed" ? false : 2_000;
    },
  });
}
