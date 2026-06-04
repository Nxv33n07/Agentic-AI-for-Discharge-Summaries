"use client";

import Link from "next/link";
import { ArrowRight, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { KNOWN_PATIENTS } from "@/lib/patients";

export default function TraceListPage() {
    return (
        <div className="space-y-6" data-testid="trace-list">
            <header className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <Activity
                        className="h-4 w-4 text-primary"
                        aria-hidden="true"
                    />
                    <h1 className="text-2xl font-bold text-primary">
                        Observability Trace
                    </h1>
                </div>
                <p className="text-sm text-foreground/70">
                    Step-by-step record of the agent's ReAct loop for each
                    patient. Pick a patient to view their trace.
                </p>
            </header>

            <div className="grid gap-3">
                {KNOWN_PATIENTS.map((p) => (
                    <Card
                        key={p.id}
                        className="hover:border-primary/30 transition-colors"
                    >
                        <CardHeader>
                            <div className="flex items-center justify-between gap-3">
                                <CardTitle className="text-base">
                                    {p.name} - {p.id}
                                </CardTitle>
                                <Badge variant="outline">trace.json</Badge>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <p className="text-sm text-foreground/70">
                                {p.summary}
                            </p>
                            <div className="mt-3">
                                <Button asChild size="sm" variant="outline">
                                    <Link
                                        href={`/trace/${p.id}`}
                                        className="flex items-center gap-1"
                                    >
                                        Open trace
                                        <ArrowRight className="h-3.5 w-3.5" />
                                    </Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
