"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    ArrowRight,
    FileText,
    Frown,
    Loader2,
} from "lucide-react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StaggerContainer, StaggerItem } from "@/components/layout/StaggerContainer";
import { getApiBase, getDraft } from "@/lib/api";
import { KNOWN_PATIENTS } from "@/lib/patients";

interface RowState {
    status: "loading" | "ready" | "missing" | "error";
    preview?: string;
    error?: string;
}

export default function DraftsListPage() {
    const [rows, setRows] = useState<Record<string, RowState>>({});

    useEffect(() => {
        let cancelled = false;
        (async () => {
            const next: Record<string, RowState> = {};
            for (const p of KNOWN_PATIENTS) {
                next[p.id] = { status: "loading" };
            }
            if (!cancelled) setRows({ ...next });

            for (const p of KNOWN_PATIENTS) {
                try {
                    const draft = await getDraft(p.id);
                    if (cancelled) return;
                    next[p.id] = {
                        status: "ready",
                        preview: draft.slice(0, 280),
                    };
                    setRows({ ...next });
                } catch (e: unknown) {
                    if (cancelled) return;
                    const msg = e instanceof Error ? e.message : "Unknown";
                    next[p.id] = {
                        status:
                            msg.toLowerCase().includes("not found") ||
                                msg.includes("404")
                                ? "missing"
                                : "error",
                        error: msg,
                    };
                    setRows({ ...next });
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <div className="space-y-6" data-testid="drafts-list">
            <header className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <FileText
                        className="h-4 w-4 text-primary"
                        aria-hidden="true"
                    />
                    <h1 className="text-2xl font-bold text-primary">Drafts</h1>
                </div>
                <p className="text-sm text-foreground/70">
                    Discharge summary drafts produced by the agent. Click a row
                    to view the full markdown.
                </p>
                <div className="text-xs text-foreground/50">
                    API: {getApiBase()}
                </div>
            </header>

            <StaggerContainer className="grid gap-3">
                {KNOWN_PATIENTS.map((p) => {
                    const row = rows[p.id] ?? { status: "loading" };
                    return (
                        <StaggerItem key={p.id}>
                            <Card className="transition-colors hover:border-primary/30">
                                <CardHeader>
                                    <div className="flex items-center justify-between gap-3">
                                        <CardTitle className="text-base">
                                            {p.name} - {p.id}
                                        </CardTitle>
                                        {row.status === "ready" && (
                                            <Badge variant="success">
                                                Draft available
                                            </Badge>
                                        )}
                                        {row.status === "loading" && (
                                            <Badge variant="muted">
                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                Checking...
                                            </Badge>
                                        )}
                                        {row.status === "missing" && (
                                            <Badge variant="warning">
                                                Not generated
                                            </Badge>
                                        )}
                                        {row.status === "error" && (
                                            <Badge variant="danger">
                                                API error
                                            </Badge>
                                        )}
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    {row.status === "loading" && (
                                        <div className="space-y-2">
                                            <Skeleton className="h-3 w-3/4" />
                                            <Skeleton className="h-3 w-1/2" />
                                        </div>
                                    )}
                                    {row.status === "ready" && (
                                        <>
                                            <p className="line-clamp-3 whitespace-pre-line text-sm text-foreground/80">
                                                {row.preview}
                                                {row.preview &&
                                                    row.preview.length >= 280
                                                    ? "..."
                                                    : ""}
                                            </p>
                                            <div className="mt-3">
                                                <Button asChild size="sm">
                                                    <Link
                                                        href={`/drafts/${p.id}`}
                                                        className="flex items-center gap-1"
                                                    >
                                                        Open full draft
                                                        <ArrowRight className="h-3.5 w-3.5" />
                                                    </Link>
                                                </Button>
                                            </div>
                                        </>
                                    )}
                                    {row.status === "missing" && (
                                        <div className="flex items-center gap-2 text-sm text-foreground/70">
                                            <Frown
                                                className="h-4 w-4 text-amber-600"
                                                aria-hidden="true"
                                            />
                                            No draft has been generated yet.
                                            Run the agent to produce one.
                                        </div>
                                    )}
                                    {row.status === "error" && (
                                        <div className="text-sm text-red-700">
                                            {row.error}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </StaggerItem>
                    );
                })}
            </StaggerContainer>
        </div>
    );
}
