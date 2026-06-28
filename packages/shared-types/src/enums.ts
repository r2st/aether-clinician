// Canonical enums. MUST stay in sync with apps/api/app/schemas/common.py.

export type AutonomyTier = 'informational' | 'suggestive' | 'flag_for_review';

export type ProbabilityBand =
  | 'high'
  | 'moderate'
  | 'low'
  | 'very_low'
  | 'insufficient_data';

export type ExtractionConfidence = 'high' | 'medium' | 'low';

export type SafetySeverity = 'info' | 'warning' | 'critical' | 'hard_block';

export type SafetyCheckType =
  | 'drug_interaction'
  | 'contraindication'
  | 'allergy_conflict'
  | 'renal_dose'
  | 'hepatic_dose';
