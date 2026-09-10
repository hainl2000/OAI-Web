// Thin fetch wrapper for the OlympicAI Scoring backend (proxied under /api).

export type Role = "admin" | "candidate";

export interface User {
  id: number;
  name: string;
  email: string | null;
  username: string | null;
  role: Role;
}

export interface AdminCompetition {
  id: number;
  name: string;
  ranking_published: boolean;
  ground_truth_version: number;
  has_ground_truth: boolean;
  registration_count: number;
  submission_count: number;
  created_at: string;
  updated_at: string;
}

export interface Registration {
  id: number;
  user: { id: number; name: string; email: string | null };
  created_at: string;
  submission_count: number;
  best_score: string | null;
}

export interface GroundTruthMeta {
  filename: string;
  size_bytes: number;
  row_count: number;
  checksum_sha256: string;
  version: number;
  uploaded_at: string;
}

export interface GroundTruthPreview {
  metadata: GroundTruthMeta;
  page: number;
  page_size: number;
  total: number;
  items: { uuid: string; is_spoof: boolean }[];
}

export interface GroundTruthReplaceResult {
  metadata: GroundTruthMeta;
  ground_truth_version: number;
  submissions_deleted: number;
}

export interface RankingEntry {
  rank: number;
  user_id: number;
  name: string;
  best_score: string;
  submission_count: number;
  best_submitted_at: string;
}

export interface Ranking {
  competition_id: number;
  competition_name: string;
  published: boolean;
  entries: RankingEntry[];
}

export interface CandidateCompetition {
  id: number;
  name: string;
  ranking_published: boolean;
  has_ground_truth: boolean;
  created_at: string;
  registered: boolean;
  registered_at: string | null;
}

export interface CandidateCompetitionDetail extends CandidateCompetition {
  ground_truth_version: number;
  my_submission_count: number;
  best_score: string | null;
}

export interface CompetitionList {
  registered: CandidateCompetition[];
  unregistered: CandidateCompetition[];
}

export interface Submission {
  id: number;
  attempt_number: number;
  score: string;
  ground_truth_version: number;
  submitted_at: string;
}

export interface RegistrationState {
  competition_id: number;
  registered: boolean;
  registered_at: string;
  created: boolean;
}

export class ApiError extends Error {
  status: number;
  code: string;
  detail: Record<string, unknown>;

  constructor(status: number, code: string, message: string, detail: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

function parseError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const d = detail as Record<string, unknown>;
      return new ApiError(
        status,
        typeof d.code === "string" ? d.code : "error",
        typeof d.message === "string" ? d.message : `Lỗi ${status}`,
        d,
      );
    }
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string; loc?: unknown[] } | undefined;
      const field = Array.isArray(first?.loc) ? String(first?.loc[first.loc.length - 1]) : "";
      const msg = first?.msg ? first.msg.replace(/^Value error, /, "") : "Dữ liệu không hợp lệ.";
      return new ApiError(status, "validation_error", field ? `${field}: ${msg}` : msg, { errors: detail });
    }
    if (typeof detail === "string") {
      return new ApiError(status, "error", detail);
    }
  }
  return new ApiError(status, "error", `Lỗi ${status}`);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isForm && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers, credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new ApiError(0, "network_error", "Không kết nối được máy chủ.");
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!response.ok) {
    throw parseError(response.status, body);
  }
  return body as T;
}

export const json = (data: unknown): string => JSON.stringify(data);

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Đã xảy ra lỗi.";
}
