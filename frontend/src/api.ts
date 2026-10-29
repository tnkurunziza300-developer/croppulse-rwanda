export type Role = 'farmer' | 'reviewer' | 'admin';
export type AccountStatus = 'active' | 'suspended';
export interface Farmer {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  status: AccountStatus;
}
export interface Farm {
  id: string;
  owner_id: string;
  name: string;
  district: string;
  sector?: string | null;
  area_ha?: number | null;
} 
export interface FarmField {
  id: string; farm_id: string; name: string; area_ha: number | null;
  latitude: number | null; longitude: number | null; archived_at: string | null;
  created_at: string; updated_at: string;
}
export interface FarmFieldCreate {
  name: string; area_ha: number | null; latitude: number | null; longitude: number | null;
}
export type CropPlanStatus =
  | 'draft'
  | 'planned'
  | 'planted'
  | 'monitoring'
  | 'harvesting'
  | 'completed'
  | 'cancelled';

export interface CropPlan {
  id: string;
  farm_id: string;
  field_id: string | null;
  district: string;
  crop: string;
  season: 'A' | 'B' | 'C';
  planting_date: string;
  area_ha: number;
  plan: Record<string, unknown>;
  verification: string;
  status: CropPlanStatus;
  actual_planting_date: string | null;
  evidence: CropPlanEvidence[];
}
export interface CropPlanEvidence {
  id: string; claim: string; crop: string | null; geographic_applicability: string | null;
  source_name: string; source_organization: string | null; source_url: string | null;
  source_identifier: string | null; publication_date: string | null; retrieval_date: string | null;
  evidence_period: string | null; units: string | null; confidence: string | null;
  limitations: string; dataset_version: string | null; recommender_version: string | null;
  generated_at: string; verification_status: string;
}
export interface CropPlanCreate {
  district: string;
  crop: string;
  season: 'A' | 'B' | 'C';
  planting_date: string;
  area_ha: number;
  field_id?: string | null;
  plan: Record<string, unknown>;
}
export type CropPlanUpdate = CropPlanCreate;
export interface CropPlanStatusUpdate {
  status: Exclude<CropPlanStatus, 'draft' | 'planned'>;
  actual_planting_date?: string;
}
export interface CropRecommendationRequest {
  district: string;
  season: 'A' | 'B' | 'C';
  elevation_m: number | null;
  irrigation: 'Unknown' | 'Yes' | 'No';
  water_availability: 'Unknown' | 'Low' | 'Medium' | 'High';
}
export interface CropRecommendation {
  crop: string; rw: string; fit: number; status: string; rank: number | null;
  water_need: string; altitude_m_range: number[];
  reasons: string[]; risks: string[]; violations: string[]; evidence: string[];
  evidence_basis: string; window: string; weak: string; source: string; next_steps: string[];
  history: { n_periods: number; years: number[]; yields: number[]; change_pct: number | null; cv_pct: number | null };
  used_stats: boolean;
  history_context_available?: boolean;
  evidence_record?: {
    rule_status: string;
    guidance_verification: string;
    approved_guidance: {
      rule_id: string; version: string; category: string; recommendation: string | null;
      geography: { type: string; scope: string[]; limitations?: string };
      season_scope: string[]; conditions: Record<string, unknown>[];
      parameters: { name: string; value: unknown; unit: string }[];
      source_references: { organization?: string; title?: string; url?: string; locator: string; paraphrase: string }[];
      limitations: string[]; effective_from: string | null; revalidate_by: string;
      status: 'approved_for_defined_scope';
    }[];
  };
}
export interface CropRecommendationResponse {
  errors: string[]; results: CropRecommendation[]; no_window: string[];
  cannot_assess: string[]; data_note: string;
  context: CropRecommendationRequest & { generated_at: string; statistics_status: string; statistics_provenance: { title?: string; publisher?: string; source_url?: string; reference_period?: string; retrieved_at?: string; units?: string; limitations?: string; sha256?: string }[]; statistics_note: string; ranking_method: string };
}
export interface Activity {
  id: string;
  farm_id: string;
  district: string;
  area_ha?: number | null;
  crop: string;
  season: string;
  activity_type: string;
  event_date: string;
  quantity?: number | null;
  unit?: string | null;
  amount_rwf?: number | null;
  notes: string;
  verification: string;
  review_status: string;
}
export interface FarmHarvest {
  id: string;
  farm_id: string;
  field_id: string | null;
  crop_plan_id: string | null;
  crop: string;
  season: 'A' | 'B' | 'C';
  harvest_date: string;
  harvested_area: number;
  area_unit: 'ha' | 'm2' | 'acre';
  quantity: number;
  quantity_unit: 'kg' | 'g' | 't' | 'lb';
  loss_quantity: number | null;
  post_harvest_observations: string | null;
  notes: string | null;
  yield_kg_ha: number | null;
  yield_calculation: string | null;
  created_at: string;
  updated_at: string;
}
export interface FarmHarvestInput {
  field_id: string | null;
  crop_plan_id: string | null;
  crop: string;
  season: 'A' | 'B' | 'C';
  harvest_date: string;
  harvested_area: number;
  area_unit: FarmHarvest['area_unit'];
  quantity: number;
  quantity_unit: FarmHarvest['quantity_unit'];
  loss_quantity: number | null;
  post_harvest_observations: string | null;
  notes: string | null;
}
export type HarvestObservationUnit = FarmHarvest['quantity_unit'];
export interface HarvestObservation {
  id: string; harvest_id: string; observed_date: string; storage_method: string | null;
  storage_location: string | null; stored_quantity: number | null; stored_unit: HarvestObservationUnit | null;
  lost_quantity: number | null; lost_unit: HarvestObservationUnit | null; condition: string | null;
  notes: string | null; follow_up: string | null; created_at: string; updated_at: string;
}
export interface HarvestObservationInput {
  observed_date: string; storage_method: string | null; storage_location: string | null;
  stored_quantity: number | null; stored_unit: HarvestObservationUnit | null;
  lost_quantity: number | null; lost_unit: HarvestObservationUnit | null;
  condition: string | null; notes: string | null; follow_up: string | null;
}
export type WaterSource = 'rainwater' | 'river' | 'lake' | 'pond_reservoir' | 'well_borehole' | 'piped_supply' | 'irrigation_scheme' | 'other' | 'unknown';
export type IrrigationMethod = 'unknown' | 'manual' | 'watering_can' | 'hose' | 'sprinkler' | 'drip' | 'furrow' | 'basin' | 'other';
export type WaterQuantityUnit = 'L' | 'm3';
export type IrrigationDurationUnit = 'minutes' | 'hours';
export interface IrrigationRecord {
  id: string; farm_id: string; field_id: string | null; crop_plan_id: string | null;
  event_date: string; water_source: WaterSource; water_source_other: string | null;
  irrigation_method: IrrigationMethod; irrigation_method_other: string | null;
  water_quantity: number | null; water_quantity_unit: WaterQuantityUnit | null;
  duration_value: number | null; duration_unit: IrrigationDurationUnit | null;
  purpose: string | null; notes: string | null; verification: 'farmer_reported';
  created_at: string; updated_at: string;
}
export type IrrigationRecordInput = Omit<IrrigationRecord, 'id' | 'farm_id' | 'verification' | 'created_at' | 'updated_at'>;
export type SoilNutrientUnit = 'mg/kg' | 'g/kg' | 'cmol/kg' | '%';
export type SoilOrganicMatterUnit = 'g/kg' | '%';
export interface SoilObservation {
  id: string; farm_id: string; field_id: string | null; observation_date: string;
  soil_description: string | null; drainage_observation: string | null; erosion_observation: string | null;
  management_practices: string | null; notes: string | null; verification: 'farmer_reported';
  created_at: string; updated_at: string;
}
export type SoilObservationInput = Omit<SoilObservation, 'id' | 'farm_id' | 'verification' | 'created_at' | 'updated_at'>;
export interface SoilTestRecord {
  id: string; farm_id: string; field_id: string | null; test_date: string; ph_value: number | null;
  nitrogen_value: number | null; nitrogen_unit: SoilNutrientUnit | null;
  phosphorus_value: number | null; phosphorus_unit: SoilNutrientUnit | null;
  potassium_value: number | null; potassium_unit: SoilNutrientUnit | null;
  organic_matter_value: number | null; organic_matter_unit: SoilOrganicMatterUnit | null;
  laboratory_name: string | null; report_reference: string | null; source_details: string | null; notes: string | null;
  verification: 'farmer_reported'; created_at: string; updated_at: string;
}
export type SoilTestRecordInput = Omit<SoilTestRecord, 'id' | 'farm_id' | 'verification' | 'created_at' | 'updated_at'>;
export type FarmTimelineEventType = 'crop_plan_created' | 'planting_recorded' | 'activity' | 'irrigation' | 'soil_observation' | 'soil_test' | 'harvest' | 'post_harvest_observation';
export interface FarmTimelineEntry {
  id: string; event_date: string | null; event_type: FarmTimelineEventType; farm_id: string; farm_name: string;
  field_id: string | null; field_name: string | null; description: string; source_label: string; href: string;
}
export interface FarmTimelineResponse { entries: FarmTimelineEntry[]; has_more: boolean; }
export interface ReviewItem extends Activity {
  farm_name: string;
  review_status: string;
  review_history: { decision: string; reason: string; reviewer_id: string; created_at: string }[];
}
export interface AdminFarmer extends Farmer {
  created_at: string;
  farm_count: number;
  reviewer_districts: string[];
}

export interface AgronomyReviewAuthorizationEvent {
  id: string; reviewer_id: string; reviewer_name: string; reviewer_email: string;
  reviewer_role: Role; action: 'grant' | 'revoke'; actor_id: string | null;
  reason: string; created_at: string;
}
export interface AgronomyRuleProposal {
  id: string; rule_id: string; version: string; title: string; category: string;
  crop_or_topic: string; proposed_claim: string; geographic_scope: { type: string; scope: string[]; limitations: string };
  season_scope: string[]; units: string[]; assumptions: string[]; limitations: string[];
  uncertainty: string; source_references: { title: string; url: string; source_version?: string | null; publication_or_revision_date?: string | null; locator: string; permission_status: string }[];
  proposed_by: string | null; revision_of_id: string | null; created_at: string;
  status: string; guidance_activation: false; guidance_note: string;
  decision_history: { id: string; reviewer_id: string | null; decision: string; rationale: string; created_at: string }[];
}
export interface MessagingReviewer { id: string; display_name: string; role_label: 'CropPulse reviewer'; eligible_districts: string[] }
export interface PrivateConversation { id: string; other_user_id: string; other_display_name: string; other_role: string; created_at: string; last_message: string | null; last_message_at: string; unread_count: number }
export interface PrivateMessage { id: string; sender_id: string; body: string; created_at: string; read_at: string | null }
export interface PrivateMessagePage { items: PrivateMessage[]; total: number; offset: number; limit: number }
export interface WeatherForecastDay {
  date: string;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  precipitation_sum_mm: number | null;
}
export interface WeatherForecast {
  status: 'available' | 'stale' | 'unavailable' | 'saved';
  source?: string;
  attribution?: string;
  retrieved_at?: string;
  forecast_type?: string;
  coordinates?: { latitude: number; longitude: number };
  daily_forecast?: WeatherForecastDay[];
  cache?: string;
  cache_age_seconds?: number;
  stored?: boolean;
  record_id?: string;
  location_context?: {
    association: 'owned_field_record' | 'coordinate_only';
    location_source: 'saved_field' | 'manual' | 'device';
    field_id: string | null;
    farm_name: string | null;
    field_name: string | null;
    geographic_verification: 'not_independently_verified';
    message: string;
  };
  message: string;
}
export interface SavedWeatherForecast {
  id: string;
  requested_coordinates: { latitude: number; longitude: number };
  status: 'available' | 'stale';
  retrieved_at: string;
  updated_at: string | null;
  location_context?: WeatherForecast['location_context'];
  forecast: WeatherForecast;
}
export interface WeatherAlertPreference {
  field_id: string; farm_id: string; farm_name: string; field_name: string;
  has_coordinates: boolean; within_supported_extent: boolean; enabled: boolean;
}
export interface WeatherAlert {
  id: string; farm_id: string | null; field_id: string | null;
  farm_name: string | null; field_name: string | null;
  alert_type: string; rule_id: string; rule_version: string; weather_source: string;
  forecast_retrieved_at: string; valid_from: string; valid_to: string; reason: string;
  evidence_status: string; evidence_snapshot: Record<string, unknown>;
  forecast_id: string | null; approval_status: 'approved' | 'inactive';
  status: 'active' | 'expired' | 'acknowledged' | 'dismissed';
  created_at: string; expires_at: string; acknowledged_at: string | null; dismissed_at: string | null;
}
export interface WeatherAlertRuleInfo {
  rule_id: string; version: string; alert_type: string; evidence_status: string;
}
export interface WeatherAlertData {
  items: WeatherAlert[]; total: number;
  active_rules: WeatherAlertRuleInfo[];
  notice: string;
}
export interface WeatherAlertPreferencesData {
  items: WeatherAlertPreference[];
  active_rules: WeatherAlertRuleInfo[];
  notice: string;
}
export interface WeatherBulletin {
  id: string; title: string; category: 'monthly' | 'seasonal'; publisher: string;
  issued_at: string; valid_from: string; valid_to: string;
  status: 'upcoming' | 'in_season' | 'past'; source_url: string;
  provenance_status: string; sha256: string; document_url: string;
}
export interface WeatherBulletinList {
  items: WeatherBulletin[]; total: number; notice: string;
}
export interface WeatherClimateRecord {
  id: string;
  record_type: 'monthly_outlook' | 'seasonal_outlook';
  variable: 'rainfall_total';
  geography_type: 'national' | 'named_area';
  geography_label: string;
  period_label: string;
  valid_from: string;
  valid_to: string;
  period_status: 'upcoming' | 'current' | 'past';
  value_min: number;
  value_max: number;
  unit: string;
  normal_min: number | null;
  normal_max: number | null;
  anomaly_label: string | null;
  source_text: string;
  source_page: number;
  transcription_status: string;
  bulletin: {
    id: string; title: string; issued_at: string; source_url: string;
    document_url: string; sha256: string; provenance_status: string;
  };
}
export interface WeatherClimateData {
  items: WeatherClimateRecord[]; total: number;
  filters: { year: number | null; record_type: string | null; search: string | null };
  notice: string;
}
export interface NisrStatisticRecord {
  district: string; crop: string; season: 'A' | 'B' | 'C'; year: number;
  area_ha: number; production_t: number; yield_t_ha: number | null;
}
export interface NisrStatistics {
  publisher: string; title: string; source_url: string; reference_period: string; retrieved_at: string;
  units: string; limitations: string; quality_report: Record<string, unknown>;
  coverage: { n_valid: number; missing_districts: string[]; coverage_label: string };
  available_years: number[]; available_seasons: string[]; available_districts: string[];
  available_crops: string[]; records: NisrStatisticRecord[];
}

export type CropHealthStatus = 'submitted' | 'under_review' | 'awaiting_farmer' | 'resolved';
export type CropHealthAssessment = 'unresolved' | 'provisional_observation';
export interface CropHealthUpdate {
  id: string; author_id: string | null; author_name: string; author_role: string;
  update_type: string; assessment: CropHealthAssessment | null; message: string; created_at: string;
}
export interface CropHealthAIScreening {
  status: 'not_run' | 'unavailable' | 'unsupported_crop' | 'candidate_screening' | string;
  model_name: string | null; model_version: string | null; generated_at: string | null;
  score_description?: string; message: string;
  candidates: { class_name: string; label: string; model_score: number }[];
  guidance?: {
    version: string; title: string; steps: string[]; treatment_notice: string;
    candidates: { name: string; organism: string | null; code: string | null; url: string | null }[];
    sources: { name: string; url: string; scope: string }[];
  };
}
export interface CropHealthCase {
  id: string; farm_id: string; farm_name: string; district: string; field_id: string | null;
  field_name: string | null; crop_plan_id: string | null; crop_plan_status: string | null;
  farmer_id: string; farmer_name?: string; crop: string; symptoms: string; observed_date: string | null;
  plant_parts_affected: string | null; spreading: boolean | null;
  ai_screening: CropHealthAIScreening;
  status: CropHealthStatus; diagnosis_status: CropHealthAssessment; photo_url: string;
  photo_size_bytes: number; photo_width: number; photo_height: number;
  created_at: string; updated_at: string; updates?: CropHealthUpdate[];
}

export function resolveApiBaseUrl(configuredBaseUrl: string | undefined, pageHostname: string): string {
  const configured = (configuredBaseUrl ?? 'http://127.0.0.1:8001').replace(/\/$/, '');
  const loopbackHosts = new Set(['localhost', '127.0.0.1']);
  if (!loopbackHosts.has(pageHostname)) return configured;

  try {
    const apiUrl = new URL(configured);
    if (loopbackHosts.has(apiUrl.hostname)) apiUrl.hostname = pageHostname;
    return apiUrl.toString().replace(/\/$/, '');
  } catch {
    return configured;
  }
}

const baseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, window.location.hostname);
let csrfToken = '';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = 'ApiError'; }
}

export async function initializeCsrf(signal?: AbortSignal): Promise<void> {
  let response: Response;
  try { response = await fetch(`${baseUrl}/v1/browser-auth/csrf`, { credentials: 'include', signal }); }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, `Cannot reach the CropPulse API at ${baseUrl}. Check the API address and make sure the backend is running.`);
  }
  if (!response.ok) throw new ApiError(response.status, 'The account service is unavailable. Please try again.');
  const body = await response.json() as { csrf_token: string };
  if (typeof body.csrf_token !== 'string' || !body.csrf_token) throw new ApiError(503, 'The account service returned an invalid security token. Please try again.');
  csrfToken = body.csrf_token;
}

function safeMessage(status: number, detail: unknown, path: string, method: string): string {
  if (status === 401) return 'Your session ended. Sign in again to continue.';
  if (status === 403 && path.startsWith('/v1/messaging/') && detail === 'Private messaging is disabled by the administrator.') return 'Private messaging is currently disabled by a CropPulse administrator.';
  if (status === 403 && detail === 'Request security check failed. Refresh the page and try again.') return 'The browser security check failed. Refresh the page and make sure the app and API use the same host name (both localhost or both 127.0.0.1), then try again.';
  if (status === 403) return 'You do not have permission to do that.';
  if (status === 404 && method === 'GET' && (path === '/v1/messaging/reviewers' || path === '/v1/messaging/conversations')) {
    return 'The API at this address does not provide the messaging endpoints. Stop the old API process and restart CropPulse’s current FastAPI service on the configured port.';
  }
  if (status === 404 && method === 'POST' && path === '/v1/weather/forecast') return 'The API at this address does not provide weather forecasts yet. Restart CropPulse’s current FastAPI service, then try again.';
  if (status === 404 && method === 'POST' && path === '/v1/crop-planning/recommendations') return 'The API at this address does not support crop recommendations yet. Restart CropPulse’s current FastAPI service, then try again.';
  if (status === 404 && method === 'GET' && detail === 'Not Found' && /^\/v1\/farms\/[^/]+\/harvests$/.test(path)) {
    return 'The API at this address does not provide harvest records. Confirm it runs the current CropPulse source and that its database is migrated to the current head, then reload.';
  }
  if (status === 404 && method === 'GET' && detail === 'Not Found' && /^\/v1\/farms\/[^/]+\/irrigation-records$/.test(path)) {
    return 'The API at this address does not provide irrigation records. Confirm it runs the current CropPulse source with migration 0018, then reload.';
  }
  if (status === 404 && path === '/v1/browser-auth/password-recovery') return 'The API server does not support password recovery yet. Restart it from the current CropPulse project, then try again.';
  if (status === 404 && path === '/v1/browser-auth/email-change') return 'The API server does not support email changes yet. Restart it from the current CropPulse project, then try again.';
  if (status === 404 && path === '/v1/browser-auth/streamlit-handoff') return 'The API server at this address is out of date and does not support the CropPulse workspace sign-in handoff. Restart the current CropPulse API, then try again.';
  if (status === 404) return 'That record could not be found.';
  if (status === 409) return typeof detail === 'string' ? detail : 'That change conflicts with the current account state.';
  if (status === 422) {
    if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join(' ') || 'Please check the submitted values.';
    return typeof detail === 'string' ? detail : 'Please check the submitted values.';
  }
  if (status === 503 && (detail === 'Account email delivery is not configured by the server administrator.' || detail === 'Account email could not be delivered. Try again later.')) return detail;
  if (status >= 500 && method === 'GET' && /^\/v1\/farms\/[^/]+\/harvests(?:\/[^/]+(?:\/observations)?)?$/.test(path)) {
    return 'Harvest records could not be loaded. Check the API server log and confirm its database has migrations 0016–0018; the local database may still be at 0015.';
  }
  if (status >= 500 && method === 'GET' && /^\/v1\/farms\/[^/]+\/irrigation-records(?:\/[^/]+)?$/.test(path)) {
    return 'Irrigation records could not be loaded. Check the API server log and confirm its database has migration 0018; the local database may still be at 0015.';
  }
  if (status >= 500) return 'CropPulse is temporarily unavailable. Your changes may not have been saved.';
  return typeof detail === 'string' ? detail : 'The request could not be completed.';
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    if (!csrfToken) await initializeCsrf(init.signal ?? undefined);
    headers.set('X-CSRF-Token', csrfToken);
  }
  let response: Response;
  let payload: { detail?: unknown };
  let csrfRetried = false;
  while (true) {
    try {
      response = await fetch(`${baseUrl}${path}`, { ...init, method, headers, credentials: 'include' });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error;
      throw new ApiError(0, 'Cannot reach the CropPulse API. Check that it is running and try again.');
    }
    if (response.status === 204) return undefined as T;
    payload = await response.json().catch(() => ({})) as { detail?: unknown };
    if (!csrfRetried && !['GET', 'HEAD', 'OPTIONS'].includes(method) && response.status === 403
      && payload.detail === 'Request security check failed. Refresh the page and try again.') {
      csrfRetried = true;
      csrfToken = '';
      await initializeCsrf(init.signal ?? undefined);
      headers.set('X-CSRF-Token', csrfToken);
      continue;
    }
    break;
  }
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/v1/browser-auth/') && path !== '/v1/me') {
      window.dispatchEvent(new Event('croppulse:session-expired'));
    }
    throw new ApiError(response.status, safeMessage(response.status, payload.detail, path, method));
  }
  return payload as T;
}

export function getNisrStatistics() { return api<NisrStatistics>('/v1/agricultural-statistics/nisr'); }

export function signIn(email: string, password: string) {
  return api<Farmer>('/v1/browser-auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
}
export function registerAccount(email: string, password: string, displayName: string, privacyAccepted: boolean) {
  return api<Farmer>('/v1/browser-auth/register', { method: 'POST', body: JSON.stringify({
    email, password, display_name: displayName, privacy_notice_accepted: privacyAccepted,
  }) });
}
export function signOut() { return api<void>('/v1/browser-auth/logout', { method: 'POST' }); }
export function createStreamlitHandoff() {
  return api<{ redirect_url: string; expires_in_seconds: number }>('/v1/browser-auth/streamlit-handoff', { method: 'POST' });
}
export function exchangeReactHandoff(code: string) {
  return api<Farmer>('/v1/browser-auth/react-handoff/exchange', { method: 'POST', body: JSON.stringify({ code }) });
}
export function requestEmailChange(current_password: string, new_email: string) {
  return api<{ message: string }>('/v1/browser-auth/email-change', { method: 'POST', body: JSON.stringify({ current_password, new_email }) });
}
export function confirmEmailChange(token: string) {
  return api<{ message: string }>('/v1/browser-auth/email-change/confirm', { method: 'POST', body: JSON.stringify({ token }) });
}
export function requestPasswordRecovery(email: string) {
  return api<{ message: string }>('/v1/browser-auth/password-recovery', { method: 'POST', body: JSON.stringify({ email }) });
}
export function completePasswordReset(token: string, new_password: string) {
  return api<{ message: string }>('/v1/browser-auth/password-reset/complete', { method: 'POST', body: JSON.stringify({ token, new_password }) });
}
export function deleteAccount(current_password: string) {
  return api<void>('/v1/browser-auth/account', { method: 'DELETE', body: JSON.stringify({ current_password, confirmation: 'DELETE' }) });
}
export function listMessagingReviewers() { return api<MessagingReviewer[]>('/v1/messaging/reviewers'); }
export function listPrivateConversations() { return api<PrivateConversation[]>('/v1/messaging/conversations'); }
export function createPrivateConversation(reviewer_id: string) {
  return api<PrivateConversation>('/v1/messaging/conversations', { method: 'POST', body: JSON.stringify({ reviewer_id }) });
}
export function listPrivateMessages(conversation_id: string, offset = 0, limit = 50) {
  return api<PrivateMessagePage>(`/v1/messaging/conversations/${encodeURIComponent(conversation_id)}/messages?offset=${offset}&limit=${limit}`);
}
export function sendPrivateMessage(conversation_id: string, body: string) {
  return api<PrivateMessage>(`/v1/messaging/conversations/${encodeURIComponent(conversation_id)}/messages`, { method: 'POST', body: JSON.stringify({ body }) });
}
export function markPrivateConversationRead(conversation_id: string, message_ids: string[]) {
  return api<{ marked_read: number; read_at: string }>(`/v1/messaging/conversations/${encodeURIComponent(conversation_id)}/read`, { method: 'POST', body: JSON.stringify({ message_ids }) });
}
export function requestWeatherForecast(latitude: number, longitude: number, saveToAccount: boolean,
  location: { field_id?: string; location_source: 'saved_field' | 'manual' | 'device' } = { location_source: 'manual' }) {
  return api<WeatherForecast>('/v1/weather/forecast', { method: 'POST', body: JSON.stringify({
    latitude, longitude, save_to_account: saveToAccount, ...location,
  }) });
}
export function listSavedWeatherForecasts() {
  return api<{ items: SavedWeatherForecast[]; total: number }>('/v1/weather/forecasts');
}
export function listWeatherAlertPreferences() {
  return api<WeatherAlertPreferencesData>('/v1/weather/alert-preferences');
}
export function updateWeatherAlertPreference(fieldId: string, enabled: boolean) {
  return api<{ field_id: string; farm_id: string; enabled: boolean; active_rules: WeatherAlertRuleInfo[]; notice: string }>(
    `/v1/weather/alert-preferences/${encodeURIComponent(fieldId)}`, { method: 'PUT', body: JSON.stringify({ enabled }) },
  );
}
export function listWeatherAlerts() {
  return api<WeatherAlertData>('/v1/weather/alerts');
}
export function updateWeatherAlertStatus(alertId: string, status: 'acknowledged' | 'dismissed') {
  return api<WeatherAlert>(`/v1/weather/alerts/${encodeURIComponent(alertId)}/status`, {
    method: 'PATCH', body: JSON.stringify({ status }),
  });
}
export function listWeatherBulletins() { return api<WeatherBulletinList>('/v1/weather/bulletins'); }
export function listWeatherClimateData(filters: { year?: number; recordType?: string; search?: string }, signal?: AbortSignal) {
  const query = new URLSearchParams();
  if (filters.year) query.set('year', String(filters.year));
  if (filters.recordType) query.set('record_type', filters.recordType);
  if (filters.search?.trim()) query.set('search', filters.search.trim());
  const suffix = query.size ? `?${query.toString()}` : '';
  return api<WeatherClimateData>(`/v1/weather/climate-data${suffix}`, { signal });
}
export function weatherBulletinDocumentUrl(id: string) {
  return `${baseUrl}/v1/weather/bulletins/${encodeURIComponent(id)}/document`;
}

export function listCropHealthCrops() { return api<string[]>('/v1/crop-health/crops'); }
export function listCropHealthCases() { return api<CropHealthCase[]>('/v1/crop-health/cases'); }
export function createCropHealthCase(payload: FormData, onProgress?: (percent: number) => void) {
  if (!onProgress) return api<CropHealthCase>('/v1/crop-health/cases', { method: 'POST', body: payload });
  return new Promise<CropHealthCase>((resolve, reject) => {
    let csrfRetried = false;
    const send = async () => {
      try {
        if (!csrfToken) await initializeCsrf();
      } catch (cause) { reject(cause); return; }
      const request = new XMLHttpRequest();
      request.open('POST', `${baseUrl}/v1/crop-health/cases`);
      request.withCredentials = true;
      request.timeout = 60_000;
      request.setRequestHeader('X-CSRF-Token', csrfToken);
      request.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && event.total > 0) onProgress(Math.min(100, Math.round(event.loaded / event.total * 100)));
      });
      request.addEventListener('error', () => reject(new ApiError(0, 'Cannot reach the CropPulse API. Check that it is running and try again.')));
      request.addEventListener('timeout', () => reject(new ApiError(0, 'The report upload took too long. Check your connection and try again.')));
      request.addEventListener('load', () => {
        let response: { detail?: unknown } & Partial<CropHealthCase> = {};
        try { response = JSON.parse(request.responseText) as typeof response; } catch { /* handled below */ }
        if (!csrfRetried && request.status === 403 && response.detail === 'Request security check failed. Refresh the page and try again.') {
          csrfRetried = true;
          csrfToken = '';
          void initializeCsrf().then(send).catch(reject);
          return;
        }
        if (request.status === 401) window.dispatchEvent(new Event('croppulse:session-expired'));
        if (request.status < 200 || request.status >= 300) {
          reject(new ApiError(request.status, safeMessage(request.status, response.detail, '/v1/crop-health/cases', 'POST')));
          return;
        }
        if (!response.id) { reject(new ApiError(502, 'The CropPulse API returned an unreadable report confirmation.')); return; }
        resolve(response as CropHealthCase);
      });
      request.send(payload);
    };
    void send();
  });
}
export function getCropHealthCase(caseId: string) {
  return api<CropHealthCase>(`/v1/crop-health/cases/${encodeURIComponent(caseId)}`);
}
export function listReviewerCropHealthCases() { return api<CropHealthCase[]>('/v1/reviewer/crop-health/cases'); }
export function getReviewerCropHealthCase(caseId: string) {
  return api<CropHealthCase>(`/v1/reviewer/crop-health/cases/${encodeURIComponent(caseId)}`);
}
export function updateReviewerCropHealthCase(caseId: string, payload: {
  action: 'start_review' | 'request_information' | 'provide_update' | 'resolve';
  message: string; assessment?: CropHealthAssessment;
}) {
  return api<CropHealthCase>(`/v1/reviewer/crop-health/cases/${encodeURIComponent(caseId)}/updates`, {
    method: 'POST', body: JSON.stringify(payload),
  });
}
export function replyToCropHealthCase(caseId: string, message: string) {
  return api<CropHealthCase>(`/v1/crop-health/cases/${encodeURIComponent(caseId)}/reply`, {
    method: 'POST', body: JSON.stringify({ message }),
  });
}

export async function fetchCropHealthPhoto(photoUrl: string, signal?: AbortSignal): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${photoUrl}`, { credentials: 'include', signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Cannot reach the CropPulse API. Check that it is running and try again.');
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: unknown };
    if (response.status === 401) window.dispatchEvent(new Event('croppulse:session-expired'));
    throw new ApiError(response.status, safeMessage(response.status, payload.detail, photoUrl, 'GET'));
  }
  return response.blob();
}
