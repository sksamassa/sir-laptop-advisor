/** Typed client for the SIR API. Same-origin: the Next rewrite proxies /api. */

export type Direction = "min" | "max";

export interface Criterion {
  key: string;
  order: number;
  label_ru: string;
  direction: Direction;
  unit: string;
  display_decimals: number;
  indifference_threshold: number;
  preference_threshold: number;
}

export interface CriteriaResponse {
  version: string;
  criteria: Criterion[];
  vocabularies: { goals: string[]; os: string[]; form_factor: string[] };
}

export interface ModelValues {
  price: number;
  performance: number;
  memory: number;
  weight: number;
  battery: number;
  screen: number;
  warranty: number;
}

export interface ModelSnapshot {
  id: string;
  brand: string;
  model_name: string;
  price_minor: number;
  os: string;
  form_factor: string;
  values: ModelValues;
}

export interface Contribution {
  normalized: number;
  contribution: number;
}

export interface RankingItem {
  rank: number;
  model: ModelSnapshot;
  net_score: number;
  phi_plus: number;
  phi_minus: number;
  contributions: Record<string, Contribution>;
  reason: string;
}

export interface RankingResponse {
  ranking_id: string;
  algorithm_version: string;
  criteria_version: string;
  candidate_count: number;
  items: RankingItem[];
  empty_reason?: string;
  cheapest_price_minor?: number | null;
}

export interface ComparisonModel {
  id: string;
  brand: string;
  model_name: string;
  price_minor: number;
  rank: number;
  net_score: number;
}

export interface ComparisonRow {
  criterion: string;
  label_ru: string;
  direction: Direction;
  unit: string;
  values: number[];
  best_index: number;
}

export interface ComparisonResponse {
  models: ComparisonModel[];
  criteria: string[];
  rows: ComparisonRow[];
  best_overall_index: number;
}

export interface Profile {
  goals: string[];
  budget_minor: number;
  preferred_brand: string | null;
  preferred_os: string | null;
  form_factor: string | null;
  weights: Record<string, number>;
  revision: number;
  updated_at: string;
}

export interface CatalogPage {
  items: ModelSnapshot[];
  page: number;
  page_size: number;
  total: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  const text = await response.text();
  const body = text ? (JSON.parse(text) as unknown) : null;
  if (!response.ok) {
    const error = (body as { error?: { message?: string; code?: string } } | null)?.error;
    throw new ApiError(
      error?.message ?? `Ошибка запроса (${response.status})`,
      response.status,
      error?.code ?? "unknown",
    );
  }
  return body as T;
}

export function getCriteria(): Promise<CriteriaResponse> {
  return request<CriteriaResponse>("/api/v1/criteria");
}

export interface RankingPayload {
  budget_minor: number;
  goals: string[];
  weights?: Record<string, number>;
  preferred_brand?: string | null;
  preferred_os?: string | null;
  form_factor?: string | null;
  use_saved_weights?: boolean;
}

export function createRanking(payload: RankingPayload): Promise<RankingResponse> {
  return request<RankingResponse>("/api/v1/rankings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function compareRanking(
  rankingId: string,
  modelIds: string[],
): Promise<ComparisonResponse> {
  return request<ComparisonResponse>(`/api/v1/rankings/${rankingId}/comparison`, {
    method: "POST",
    body: JSON.stringify({ model_ids: modelIds }),
  });
}

export interface CatalogQuery {
  query?: string;
  brand?: string;
  os?: string;
  formFactor?: string;
  maxPriceMinor?: number;
  page?: number;
  pageSize?: number;
  sort?: string;
}

export function getCatalog(params: CatalogQuery): Promise<CatalogPage> {
  const search = new URLSearchParams();
  if (params.query) search.set("q", params.query);
  if (params.brand) search.set("brand", params.brand);
  if (params.os) search.set("os", params.os);
  if (params.formFactor) search.set("form_factor", params.formFactor);
  if (params.maxPriceMinor) search.set("max_price_minor", String(params.maxPriceMinor));
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 12));
  search.set("sort", params.sort ?? "price_asc");
  return request<CatalogPage>(`/api/v1/models?${search.toString()}`);
}

export interface SessionUser {
  id: string;
  email: string;
  role: "shopper" | "maintainer";
}

export function login(email: string, password: string): Promise<{ user: SessionUser }> {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(email: string, password: string): Promise<{ user_id: string; role: string }> {
  return request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return request("/api/v1/auth/logout", { method: "POST" });
}

export function me(): Promise<{ user: SessionUser }> {
  return request("/api/v1/auth/me");
}

export function getProfile(): Promise<Profile> {
  return request<Profile>("/api/v1/profile");
}

export interface ProfilePayload {
  goals: string[];
  budget_minor: number;
  preferred_brand: string | null;
  preferred_os: string | null;
  form_factor: string | null;
  weights: Record<string, number>;
}

export function saveProfile(payload: ProfilePayload, partial = false): Promise<Profile> {
  return request<Profile>("/api/v1/profile", {
    method: partial ? "PATCH" : "PUT",
    body: JSON.stringify(payload),
  });
}
