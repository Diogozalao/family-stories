export interface MediaFile {
  id: number;
  filename: string;
  file_path?: string;
  media_type: string;
  size?: number;
  taken_at?: string | null;
  created_at?: string;
  description?: string | null;
}

export interface Person {
  id: number;
  name: string;
  birth_date?: string | null;
  birth_place?: string | null;
  gedcom_id?: string | null;
}

export interface TimelineEvent {
  id: number;
  event_date?: string | null;
  title?: string | null;
  description?: string | null;
  media_file_id?: number | null;
}

export interface Story {
  id: number;
  title: string;
  event_type: string;
  content: string;
  created_at: string;
  word_count?: number;
}

export interface Video {
  id: number;
  story_id: number;
  filename: string | null;
  size_mb: number | null;
  photos_used: number | null;
  status: string;
  error_message?: string | null;
  created_at: string;
  download_url?: string | null;
}

export type TaskState = "pending" | "running" | "done" | "failed";
export type TaskKind  = "narrative" | "video" | "ingest";

export interface TaskRecord {
  id: number;
  celery_id?: string | null;
  kind: TaskKind;
  state: TaskState;
  story_id?: number | null;
  video_id?: number | null;
  payload?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface NarrativeTemplate {
  id: string;
  name: string;
  tone: string;
  structure: string;
}

export interface HealthCheck {
  status: "ok" | "degraded" | "error";
  failures: string[];
  warnings: string[];
  checks: Record<string, { status: string; [k: string]: unknown }>;
}
