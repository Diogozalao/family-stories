export interface MediaFile {
  id: number;
  original_filename: string;
  media_type: string;
  file_size?: number;
  status?: string;
  date_taken?: string | null;
  created_at?: string;
  ai_description?: string | null;
  ai_setting?: string | null;
  ai_emotion?: string | null;
  ai_people_count?: number | null;
  ai_tags?: string[] | null;
  latitude?: number | null;
  longitude?: number | null;
  location_name?: string | null;
  camera_make?: string | null;
  camera_model?: string | null;
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
  narrative: string;
  template_used?: string | null;
  llm_backend?: string | null;
  facts_used?: number;
  status?: "draft" | "completed" | "failed";
  created_at: string;
}

export type VideoStatus = "processing" | "completed" | "failed";

export interface Video {
  id: number;
  story_id: number;
  filename: string | null;
  size_mb: number | null;
  photos_used: number | null;
  status: VideoStatus;
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
