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
  stored_comment_count: number;
  scan_status: 'not_scanned' | 'queued' | 'running' | 'done' | 'failed';
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

export interface CommentItem {
  comment_id: string;
  video_id: string;
  author_name: string | null;
  author_channel_id: string | null;
  text_original: string;
  published_at: string | null;
  like_count: number;
  zone: 'judol' | 'review' | 'bukan' | null;
  score: number | null;
  rule_hit: boolean;
  model_version: string | null;
  classified_at: string | null;
  moderation_status: 'none' | 'rejected' | 'failed';
}

export interface CommentsData {
  items: CommentItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  zone: string | null;
  search: string | null;
  sort: string;
  moderation_status: 'active' | 'rejected' | 'all';
}

export interface JobData {
  id: string;
  type: 'scan' | 'fetch' | 'classify' | 'extract';
  video_id: string | null;
  status: 'queued' | 'running' | 'done' | 'failed';
  progress: number;
  total: number;
  processed: number;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface KeywordItem {
  id: number;
  video_id: string;
  keyword: string;
  type: 'situs' | 'kata_kunci';
  frequency: number;
  extracted_at: string | null;
}

export interface KeywordsData {
  video_id: string;
  total: number;
  items: KeywordItem[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  tool_used: string[];
  provider: string | null;
  model: string | null;
  fallback: boolean;
}

export interface ChatLogItem {
  id: number;
  session_id?: string | null;
  question: string;
  tool_used: string[];
  answer: string;
  created_at: string | null;
}

export interface ChatHistoryData {
  items: ChatLogItem[];
  total: number;
}

export interface ChatSession {
  id: string;
  video_id: string | null;
  title: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChatSessionsData {
  items: ChatSession[];
  total: number;
}

export interface ChatMessagesData {
  session_id: string;
  items: ChatLogItem[];
  total: number;
}

export interface RejectPreviewData {
  estimate: {
    comment_count: number;
    batch_count: number;
    ids_per_batch: number;
    estimated_quota_units: number;
    remaining_quota_units: number;
    sufficient: boolean;
  };
  quota: {
    date: string;
    used_units: number;
    daily_limit: number;
    remaining_units: number;
    updated_at: string | null;
  };
}

export interface RejectSummary {
  requested: number;
  succeeded: number;
  failed: number;
  comment_count: number;
  batch_count: number;
  ids_per_batch: number;
  estimated_quota_units: number;
  rejected: string[];
  failures: Array<{ comment_id: string; error: string }>;
  quota: RejectPreviewData['quota'];
}
