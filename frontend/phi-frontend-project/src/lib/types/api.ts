/**
 * Types mirror backend/main.py exactly:
 * - RedactionResponse (POST /redact)
 * - RestoreResponse (POST /restore)
 * The backend is not modified, so these fields must stay in sync with it.
 */

export interface RedactionResponse {
  status: string;
  session_id: string;
  redacted_text: string;
  emails_found: number;
  phones_found: number;
  faxes_found: number;
  ips_found: number;
  names_found: number;
  mrns_found: number;
  ssns_found: number;
  dobs_found: number;
  ages_found: number;
  addresses_found: number;
  locations_found: number;
  facilities_found: number;
  urls_found: number;
  account_numbers_found: number;
  health_plan_ids_found: number;
  device_ids_found: number;
  vins_found: number;
  licenses_found: number;
}

export interface RestoreResponse {
  status: string;
  text: string;
}

export interface HealthResponse {
  status: string;
  message?: string;
}

export interface ApiErrorPayload {
  status?: string;
  message?: string;
  detail?: string | { msg: string }[];
}

/** Keys on RedactionResponse that represent entity counters. */
export const ENTITY_COUNT_KEYS = [
  "names_found",
  "emails_found",
  "phones_found",
  "faxes_found",
  "ips_found",
  "mrns_found",
  "ssns_found",
  "dobs_found",
  "ages_found",
  "addresses_found",
  "locations_found",
  "facilities_found",
  "urls_found",
  "account_numbers_found",
  "health_plan_ids_found",
  "device_ids_found",
  "vins_found",
  "licenses_found",
] as const;

export type EntityCountKey = (typeof ENTITY_COUNT_KEYS)[number];
