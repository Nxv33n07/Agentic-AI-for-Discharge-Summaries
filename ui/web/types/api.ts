// Surface types for the Dscribe Web UI ↔ FastAPI contract.
// Mirror of the response shapes served by src/api/main.py.

export interface ProcessResponse {
  patient_id: string;
  status: "processing" | "completed" | "failed";
  message: string;
}

export interface PatientProcessResponse {
  patient_id: string;
  status: string;
  message: string;
}

export interface DraftResponse {
  id?: string;
  patient_id?: string;
  content: string;
  status?: string; // "generated" | "reviewed" | "approved"
  confidence_score?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TraceStep {
  step_number: number;
  action: string;
  observation: string;
  timestamp: string;
  tool?: string;
  rationale?: string;
  input?: unknown;
  result?: string | unknown;
  next_plan?: string;
}

export interface TraceResponse {
  id?: string;
  patient_id: string;
  steps: TraceStep[];
  escalations: string[];
  created_at?: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  services: {
    api: string;
    agent: string;
    learning: string;
  };
}

export interface LearningRule {
  from: string;
  to: string;
  count: number;
}

export interface LearningStats {
  total_iterations: number;
  avg_normalized_edit_distance: number;
  memory_size: number;
  learned_substitution_rules: LearningRule[];
}
