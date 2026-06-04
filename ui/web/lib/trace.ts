/**
 * lib/trace.ts — Normalize the agent trace shape from the FastAPI backend.
 *
 * The Python agent writes StepTrace to output/<patient>/trace.json. Depending
 * on the version, the step records use slightly different keys (e.g.
 * step_number vs step, action vs rationale). This module picks a reasonable
 * representation for the UI regardless of which keys exist.
 */

export interface NormalizedStep {
    step: number;
    title: string;
    rationale: string;
    tool?: string;
    input?: unknown;
    result?: string;
    next_plan?: string;
    timestamp?: string;
}

function pickStr(obj: Record<string, unknown>, keys: string[]): string | undefined {
    for (const k of keys) {
        const v = obj[k];
        if (typeof v === "string" && v.length) return v;
    }
    return undefined;
}

function pickNum(obj: Record<string, unknown>, keys: string[]): number | undefined {
    for (const k of keys) {
        const v = obj[k];
        if (typeof v === "number") return v;
        if (typeof v === "string" && v && !isNaN(Number(v))) return Number(v);
    }
    return undefined;
}

export function normalizeTrace(raw: unknown): NormalizedStep[] {
    if (!raw) return [];

    // Some implementations wrap the steps in { steps: [...] }
    let arr: unknown[] = [];
    if (Array.isArray(raw)) {
        arr = raw as unknown[];
    } else if (typeof raw === "object") {
        const obj = raw as Record<string, unknown>;
        for (const k of ["steps", "plan_history", "history"]) {
            if (Array.isArray(obj[k])) {
                arr = obj[k] as unknown[];
                break;
            }
        }
    }

    return arr
        .map((entry, idx) => {
            if (!entry || typeof entry !== "object") return null;
            const o = entry as Record<string, unknown>;
            const step = pickNum(o, ["step", "step_number", "index", "n"]) ?? idx + 1;
            const rationale =
                pickStr(o, ["rationale", "reasoning", "thought", "action"]) ?? "";
            const tool = pickStr(o, ["tool", "tool_name", "name"]);
            const input = o["input"] ?? o["params"] ?? o["arguments"];
            const result =
                pickStr(o, ["result", "observation", "output", "response"]) ?? "";
            const next_plan = pickStr(o, ["next_plan", "next", "plan"]);
            const timestamp = pickStr(o, ["timestamp", "ts", "time"]);
            return {
                step,
                title: `Step ${step}`,
                rationale,
                tool,
                input,
                result,
                next_plan,
                timestamp,
            } as NormalizedStep;
        })
        .filter((x): x is NormalizedStep => x !== null);
}
