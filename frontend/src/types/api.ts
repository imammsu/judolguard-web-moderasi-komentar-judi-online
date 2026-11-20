// Kontrak respons API - harus sinkron dengan backend/app/responses.py & blueprints/health.py

export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiFailure {
  success: false;
  error: ApiErrorBody;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export interface MlStatus {
  model_loaded: boolean;
  model_version: string;
  load_error: string | null;
  load_seconds: number | null;
  sklearn_version: string;
  expected_sklearn_version: string | null;
  sklearn_version_match: boolean;
  normalizer_hash: string | null;
  expected_normalizer_hash: string | null;
  normalizer_match: boolean;
  thresholds: { t_low: number; t_high: number } | null;
}

export interface HealthData {
  status: 'ok' | 'degraded';
  app: string;
  version: string;
  environment: string;
  ml: MlStatus;
  database: {
    configured: boolean;
    connected: boolean;
    mode: 'session_pooler';
    error: string | null;
  };
  integrations: {
    google_oauth_configured: boolean;
    gemini_configured: boolean;
    groq_configured: boolean;
  };
}

export interface UserProfile {
  channel_id: string;
  channel_title: string;
  email: string;
  thumbnail_url: string;
  custom_url: string | null;
}

export interface MeData {
  authenticated: boolean;
  user: UserProfile;
}

export interface VideoItem {
  video_id: string;
  title: string;
  thumbnail_url: string;
  published_at: string | null;
  comment_count: number;
  last_fetched_at: string | null;
}

export interface VideosData {
  items: VideoItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  refreshed: boolean;
  synced_count: number;
  sync_mode: 'cache' | 'initial' | 'incremental' | 'full_refresh';
  new_videos: number;
  updated_videos: number;
  metadata_batches: number;
  estimated_quota: number;
}
