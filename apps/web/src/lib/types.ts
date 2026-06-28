// Shared API types (mirror of apps/api Pydantic schemas — Phase 1 subset).

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Account {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface PatientSummary {
  id: string;
  full_name: string;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  consent_given: boolean;
  updated_at: string;
}

export interface Patient extends PatientSummary {
  address_text: string | null;
  notes: string | null;
  consent_given_at: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  pagination: { total: number; limit: number; offset: number; has_more: boolean };
}

export interface DocumentResponse {
  id: string;
  patient_id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  document_type: string | null;
  extraction_status: string;
  ocr_fallback_used: boolean;
  created_at: string;
}

export interface ExtractionField {
  name: string;
  value: unknown;
  confidence: number;
  confidence_band: 'high' | 'medium' | 'low';
  needs_confirmation: boolean;
}

export interface ExtractedEntity {
  entity_type: string;
  fields: ExtractionField[];
  region: unknown;
}

export interface ExtractionResult {
  document_id: string;
  document_type: string | null;
  model: string | null;
  ocr_fallback_used: boolean;
  entities: ExtractedEntity[];
  confirmation_required_count: number;
}

export interface LongitudinalRecord {
  patient_id: string;
  medications: Array<Record<string, unknown>>;
  lab_results: Array<Record<string, unknown>>;
  conditions: Array<Record<string, unknown>>;
  allergies: Array<Record<string, unknown>>;
  derived_markers: Array<Record<string, unknown>>;
}

export interface SafetyFlag {
  check_type: string;
  severity: 'info' | 'warning' | 'critical' | 'hard_block';
  is_hard_block: boolean;
  summary: string;
  details: Record<string, unknown>;
}

export interface SafetyCheckResponse {
  patient_id: string;
  proposed_drug_reference_id: string;
  proposed_drug_name: string;
  is_blocked: boolean;
  is_hard_block: boolean;
  checked_against: Record<string, unknown>;
  flags: SafetyFlag[];
  offline_capable: boolean;
}

export interface AuditEntry {
  id: string;
  sequence: number;
  action: string;
  entity_type: string | null;
  payload: Record<string, unknown>;
  record_hash: string;
  prev_hash: string;
  created_at: string;
}
