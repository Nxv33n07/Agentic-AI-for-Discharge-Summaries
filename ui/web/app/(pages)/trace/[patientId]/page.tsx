"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
    Activity,
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    ShieldAlert,
    Wrench,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { StaggerContainer, StaggerItem } from "@/components/layout/StaggerContainer";
import { getTrace } from "@/lib/api";
import type { TraceResponse, TraceStep } from "@/types/api";
import { KNOWN_PATIENTS, getPatientInfo } from "@/lib/patients";

function tryParseJsonString(s: unknown): string {
    if (s == null) return "";
    if (typeof s !== "string") return JSON.stringify(s, null, 2);
    const trimmed = s.trim();
    if (
        (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
        (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
        try {
            return JSON.stringify(JSON.parse(trimmed), null, 2);
        } catch {
            return s;
        }
    }
    return s;
}

function isEscalation(text: string): boolean {
    const t = text.toLowerCase();
    return (
        t.includes("flag") ||
        t.includes("escalat") ||
        t.includes("missing") ||
        t.includes("conflict") ||
        t.includes("pending") ||
        t.includes("not documented") ||
        t.includes("unclear")
    );
}

export default function TraceDetailPage() {
    const params = useParams<{ patientId: string }>();
    const router = useRouter();
    const patientId = params?.patientId ?? "";
    const info = getPatientInfo(patientId);
    const [trace, setTrace] = useState<TraceResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState<Record<number, boolean>>({});

    const valid = KNOWN_PATIENTS.some((p) => p.id === patientId);

    useEffect(() => {
        if (!valid) return;
        setLoading(true);
        setError(null);
        getTrace(patientId)
            .then((t) => setTrace(t as TraceResponse))
            .catch((e: unknown) =>
                setError(e instanceof Error ? e.message : "Unknown error")
            )
            .finally(() => setLoading(false));
    }, [patientId, valid]);

    const steps = useMemo<TraceStep[]>(
        () => (trace && Array.isArray(trace.steps) ? trace.steps : []),
        [trace]
    );

    const escalations = useMemo<string[]>(
        () => (trace?.escalations ?? []).filter(Boolean),
        [trace]
    );

    const flaggedSteps = useMemo<Set<number>>(() => {
        const s = new Set<number>();
        steps.forEach((st, i) => {
            const haystack = [
                st.action,
                st.rationale ?? "",
                st.observation ?? "",
                typeof st.result === "string" ? st.result : "",
            ].join(" ");
            if (isEscalation(haystack)) s.add(i);
        });
        return s;
    }, [steps]);

    if (!valid) {
        return (
            <Card>
                <CardContent className="p-8 text-center">
                    <p className="text-sm text-foreground/70">
                        Unknown patient id: {patientId}
                    </p>
                    <Button asChild className="mt-3" variant="outline">
                        <Link href="/trace">Back to trace list</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6" data-testid="trace-detail">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push("/trace")}
                        aria-label="Back to trace list"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Back
                    </Button>
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <Activity
                                className="h-4 w-4 text-primary"
                                aria-hidden="true"
                            />
                            <h1 className="text-2xl font-bold text-primary">
                                Trace - {info?.name ?? patientId}
                            </h1>
                            <Badge variant="outline">{patientId}</Badge>
                            {escalations.length > 0 && (
                                <Badge variant="warning" className="gap-1">
                                    <AlertTriangle className="h-3 w-3" />
                                    {escalations.length} escalation
                                    {escalations.length === 1 ? "" : "s"}
                                </Badge>
                            )}
                        </div>
                        <p className="text-sm text-foreground/60">
                            {steps.length} step
                            {steps.length === 1 ? "" : "s"} ·{" "}
                            {flaggedSteps.size} flagged
                        </p>
                    </div>
                </div>
                <Button asChild size="sm" variant="outline">
                    <Link href={`/drafts/${patientId}`}>View draft</Link>
                </Button>
            </div>

            {escalations.length > 0 && (
                <Alert
                    variant="warning"
                    icon={<ShieldAlert className="h-4 w-4" />}
                >
                    <AlertTitle>
                        Flags and escalations detected
                    </AlertTitle>
                    <AlertDescription>
                        <ul className="ml-4 list-disc space-y-1 text-sm">
                            {escalations.map((e, i) => (
                                <li key={i}>{e}</li>
                            ))}
                        </ul>
                    </AlertDescription>
                </Alert>
            )}

            {error && (
                <Alert variant="danger">
                    <AlertTitle>Could not load trace</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {loading && (
                <div className="space-y-2">
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                </div>
            )}

            {!loading && !error && steps.length === 0 && (
                <Card>
                    <CardContent className="p-8 text-center text-sm text-foreground/70">
                        No trace available yet. Run the agent to generate
                        one.
                    </CardContent>
                </Card>
            )}

            {!loading && !error && steps.length > 0 && (
                <ol
                    className="space-y-3"
                    data-testid="trace-panel"
                    aria-label="Agent trace steps"
                >
                    <StaggerContainer className="space-y-3">
                        {steps.map((s, i) => {
                            const isOpen = expanded[i] ?? false;
                            const flagged = flaggedSteps.has(i);
                            return (
                                <StaggerItem key={i}>
                                    <Card
                                        className={
                                            flagged
                                                ? "border-amber-300/70 bg-amber-50/30"
                                                : ""
                                        }
                                    >
                                        <button
                                            type="button"
                                            onClick={() =>
                                                setExpanded((prev) => ({
                                                    ...prev,
                                                    [i]: !isOpen,
                                                }))
                                            }
                                            aria-expanded={isOpen}
                                            className="w-full text-left"
                                        >
                                            <div className="flex items-center gap-3 p-4">
                                                <div
                                                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${flagged
                                                            ? "bg-amber-100 text-amber-800"
                                                            : "bg-primary/10 text-primary"
                                                        }`}
                                                >
                                                    {(s.step_number ?? i + 1)}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span
                                                            className={`text-sm font-semibold ${flagged
                                                                    ? "text-amber-800"
                                                                    : "text-primary"
                                                                }`}
                                                        >
                                                            Step{" "}
                                                            {s.step_number ?? i + 1}
                                                        </span>
                                                        {flagged && (
                                                            <Badge variant="warning">
                                                                Flagged
                                                            </Badge>
                                                        )}
                                                        {s.tool && (
                                                            <Badge variant="default">
                                                                <Wrench className="h-3 w-3" />
                                                                {s.tool}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    <p className="mt-1 line-clamp-2 text-sm text-foreground/80">
                                                        {s.action ||
                                                            s.rationale ||
                                                            s.observation}
                                                    </p>
                                                </div>
                                                <div className="shrink-0 text-foreground/50">
                                                    {isOpen ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                    )}
                                                </div>
                                            </div>
                                        </button>
                                        {isOpen && (
                                            <CardContent className="space-y-3 border-t border-primary/10 pt-4 text-sm">
                                                {s.next_plan && (
                                                    <div>
                                                        <div className="text-xs font-semibold uppercase tracking-wide text-foreground/50">
                                                            Next plan
                                                        </div>
                                                        <p className="text-foreground/85">
                                                            {s.next_plan}
                                                        </p>
                                                    </div>
                                                )}
                                                {s.input !== undefined && (
                                                    <div>
                                                        <div className="text-xs font-semibold uppercase tracking-wide text-foreground/50">
                                                            Tool input
                                                        </div>
                                                        <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-slate-950/90 p-3 font-mono text-xs text-slate-100">
                                                            {tryParseJsonString(
                                                                s.input
                                                            )}
                                                        </pre>
                                                    </div>
                                                )}
                                                {s.result !== undefined && (
                                                    <div>
                                                        <div className="text-xs font-semibold uppercase tracking-wide text-foreground/50">
                                                            Tool result
                                                        </div>
                                                        <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-slate-950/90 p-3 font-mono text-xs text-slate-100">
                                                            {tryParseJsonString(
                                                                s.result
                                                            )}
                                                        </pre>
                                                    </div>
                                                )}
                                                {!s.input &&
                                                    !s.result &&
                                                    !s.next_plan && (
                                                        <div className="flex items-center gap-2 text-emerald-700">
                                                            <CheckCircle2 className="h-4 w-4" />
                                                            Step completed
                                                            without additional
                                                            tool calls.
                                                        </div>
                                                    )}
                                            </CardContent>
                                        )}
                                    </Card>
                                </StaggerItem>
                            );
                        })}
                    </StaggerContainer>
                </ol>
            )}
        </div>
    );
}
