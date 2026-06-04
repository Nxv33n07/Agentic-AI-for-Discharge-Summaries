/**
 * lib/api.ts — Typed client for the Dscribe FastAPI backend.
 *
 * Base URL is read from NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 * Surface types live in @/types/api (defined in types/api.ts).
 */

import type {
  PatientProcessResponse,
  TraceResponse,
  DraftResponse,
  HealthResponse,
  LearningStats,
} from "@/types/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type {
  PatientProcessResponse,
  TraceResponse,
  DraftResponse,
  HealthResponse,
  LearningStats,
};
export type { ProcessResponse } from "@/types/api";

export async function checkHealth(): Promise<HealthResponse> {
  const r = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
  if (!r.ok) throw new Error(`Health check failed: ${r.status}`);
  return r.json();
}

export async function processPatient(
  patientId: string,
  options: { sync?: boolean; outputDir?: string } = {}
): Promise<PatientProcessResponse> {
  const r = await fetch(`${API_BASE}/api/v1/process_patient`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_id: patientId,
      output_dir: options.outputDir ?? "output",
      sync: options.sync ?? true,
    }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(
      err?.detail ??
      `Process patient failed: ${r.status} ${r.statusText}`
    );
  }
  return r.json();
}

export async function getDraftResponse(
  patientId: string,
  outputDir = "output"
): Promise<DraftResponse> {
  const r = await fetch(
    `${API_BASE}/api/v1/draft/${patientId}?output_dir=${outputDir}`,
    { cache: "no-store" }
  );
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err?.detail ?? `Get draft failed: ${r.status}`);
  }
  return r.json();
}

/**
 * Returns the raw markdown text for a draft. Accepts both the modern
 * { content, ... } shape and the legacy { draft: string } shape.
 */
export async function getDraft(
  patientId: string,
  outputDir = "output"
): Promise<string> {
  const r = await fetch(
    `${API_BASE}/api/v1/draft/${patientId}?output_dir=${outputDir}`,
    { cache: "no-store" }
  );
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err?.detail ?? `Get draft failed: ${r.status}`);
  }
  const data: { draft?: string; content?: string } = await r.json();
  return data.content ?? data.draft ?? "";
}

export async function getTrace(
  patientId: string,
  outputDir = "output"
): Promise<TraceResponse> {
  const r = await fetch(
    `${API_BASE}/api/v1/trace/${patientId}?output_dir=${outputDir}`,
    { cache: "no-store" }
  );
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err?.detail ?? `Get trace failed: ${r.status}`);
  }
  return r.json();
}

export async function getLearningStats(): Promise<LearningStats | null> {
  try {
    const r = await fetch(`${API_BASE}/api/v1/learning/stats`, {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export function getApiBase(): string {
  return API_BASE;
}
