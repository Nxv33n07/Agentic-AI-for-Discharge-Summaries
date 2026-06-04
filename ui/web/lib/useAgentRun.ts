"use client";

import { useCallback, useState } from "react";
import { processPatient, getDraft, getTrace } from "@/lib/api";
import type { TraceResponse } from "@/types/api";

export type RunStatus = "idle" | "running" | "success" | "error";

export interface AgentRunResult {
    patientId: string;
    draft: string;
    trace: TraceResponse | null;
}

export function useAgentRun() {
    const [status, setStatus] = useState<RunStatus>("idle");
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<AgentRunResult | null>(null);
    const [lastRunAt, setLastRunAt] = useState<number | null>(null);

    const run = useCallback(async (patientId: string) => {
        setStatus("running");
        setError(null);
        try {
            const resp = await processPatient(patientId, { sync: true });
            if (
                "status" in resp &&
                (resp as { status?: string }).status === "failed"
            ) {
                throw new Error(
                    (resp as { message?: string }).message ||
                    "Agent run reported failure"
                );
            }
            const [draft, trace] = await Promise.all([
                getDraft(patientId),
                getTrace(patientId).catch(() => null),
            ]);
            setResult({ patientId, draft, trace });
            setLastRunAt(Date.now());
            setStatus("success");
            return { patientId, draft, trace };
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Unknown error";
            setError(msg);
            setStatus("error");
            throw e;
        }
    }, []);

    const reset = useCallback(() => {
        setStatus("idle");
        setError(null);
        setResult(null);
        setLastRunAt(null);
    }, []);

    return { status, error, result, lastRunAt, run, reset };
}
