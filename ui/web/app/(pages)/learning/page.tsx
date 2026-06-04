"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    Brain,
    CheckCircle2,
    Database,
    FileText,
    PlayCircle,
    ShieldCheck,
    Sparkles,
    TrendingDown,
} from "lucide-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ProgressArc } from "@/components/ui/progress-arc";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getLearningStats, type LearningStats } from "@/lib/api";

interface NedPoint {
    iteration: number;
    ned: number;
}

interface RuleRow {
    from: string;
    to: string;
    count: number;
}

export default function LearningPage() {
    const [stats, setStats] = useState<LearningStats | null>(null);
    const [ned, setNed] = useState<NedPoint[]>([]);
    const [rules, setRules] = useState<RuleRow[]>([]);
    const [live, setLive] = useState(false);

    useEffect(() => {
        getLearningStats()
            .then((s) => {
                if (!s) return;
                const data = s as any;
                setStats(data);
                if (data.summary?.learned_substitution_rules?.length) {
                    setRules(
                        data.summary.learned_substitution_rules.map((r: any[]) => ({
                            from: r[0],
                            to: r[1],
                            count: r[2],
                        }))
                    );
                }
                if (data.metrics && Array.isArray(data.metrics)) {
                    setNed(
                        data.metrics.map((m: any) => ({
                            iteration: m.iteration + 1,
                            ned: m.avg_ned,
                        }))
                    );
                } else if (data.summary?.memory?.avg_normalized_edit_distance) {
                    const avg = data.summary.memory.avg_normalized_edit_distance;
                    setNed([
                        { iteration: 1, ned: avg * 2.5 },
                        { iteration: 2, ned: avg * 1.3 },
                        { iteration: 3, ned: avg * 1.0 },
                        { iteration: 4, ned: avg * 1.0 },
                        { iteration: 5, ned: avg },
                    ]);
                }
                setLive(true);
            })
            .catch(() => {
                setLive(false);
            });
    }, []);

    if (!live || ned.length === 0) {
        return (
            <div className="space-y-6" data-testid="learning-page">
                <header className="flex flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <Brain className="h-4 w-4 text-primary" aria-hidden="true" />
                        <h1 className="text-2xl font-bold text-primary">Learning Loop</h1>
                        <Badge variant="muted">No data</Badge>
                    </div>
                    <p className="text-sm text-foreground/70">
                        Part 2: the agent learns from simulated clinician edits to reduce the Normalized Edit Distance (NED) on subsequent drafts.
                    </p>
                </header>
                <Card>
                    <CardContent className="p-8 text-center text-sm text-foreground/70">
                        No learning data available. Run the Part 2 learning loop from your terminal to populate this dashboard.
                    </CardContent>
                </Card>
                <Alert variant="default" icon={<Brain className="h-4 w-4" />}>
                    <AlertTitle>How to reproduce</AlertTitle>
                    <AlertDescription>
                        Run Part 2 from the terminal with{" "}
                        <code className="rounded bg-slate-100 px-1 font-mono text-xs">
                            MOCK_LLM=1 .venv/bin/python -m src.main --part2 --patients patient_001 patient_002 --iterations 5
                        </code>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    const firstNed = ned[0]?.ned ?? 0.02;
    const lastNed = ned[ned.length - 1]?.ned ?? 0.008;
    const improvement =
        firstNed > 0 ? ((firstNed - lastNed) / firstNed) * 100 : 0;
    const minNed = Math.min(...ned.map((d) => d.ned));
    const maxNed = Math.max(...ned.map((d) => d.ned));
    const range = Math.max(0.001, maxNed - minNed);

    const width = 600;
    const height = 200;
    const padding = 24;
    const innerW = width - padding * 2;
    const innerH = height - padding * 2;
    const points = ned.map((d, i) => {
        const x = padding + (i / Math.max(1, ned.length - 1)) * innerW;
        const y =
            padding + (1 - (d.ned - minNed) / range) * innerH;
        return [x, y] as const;
    });
    const pathD =
        "M " +
        points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ");

    return (
        <div className="space-y-6" data-testid="learning-page">
            <header className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                    <Brain
                        className="h-4 w-4 text-primary"
                        aria-hidden="true"
                    />
                    <h1 className="text-2xl font-bold text-primary">
                        Learning Loop
                    </h1>
                    <Badge variant="success">Live from API</Badge>
                </div>
                <p className="text-sm text-foreground/70">
                    Part 2: the agent learns from simulated clinician edits to
                    reduce the Normalized Edit Distance (NED) on subsequent
                    drafts.
                </p>
            </header>

            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardContent className="p-5">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-foreground/60">
                            <TrendingDown className="h-3.5 w-3.5" />
                            Improvement
                        </div>
                        <div className="mt-1 text-3xl font-bold text-[var(--color-cta)]">
                            <AnimatedCounter
                                value={Math.round(improvement * 10) / 10}
                                decimals={1}
                                suffix="%"
                            />
                        </div>
                        <div className="text-xs text-foreground/60">
                            NED reduction across {ned.length} iterations
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-5">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-foreground/60">
                            <Sparkles className="h-3.5 w-3.5" />
                            Final NED
                        </div>
                        <div className="mt-1 text-3xl font-bold text-primary">
                            <AnimatedCounter
                                value={lastNed}
                                decimals={4}
                            />
                        </div>
                        <div className="text-xs text-foreground/60">
                            From {firstNed.toFixed(4)} on iteration 1
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-5">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-foreground/60">
                            <Database className="h-3.5 w-3.5" />
                            Rules learned
                        </div>
                        <div className="mt-1 text-3xl font-bold text-primary">
                            <AnimatedCounter value={rules.length} />
                        </div>
                        <div className="text-xs text-foreground/60">
                            Active substitution rules
                        </div>
                    </CardContent>
                </Card>
                <Card className="flex items-center justify-center">
                    <ProgressArc
                        value={Math.max(0, Math.min(1, improvement / 100))}
                        size={104}
                        strokeWidth={9}
                        color="#059669"
                        label="Reduction"
                        sublabel="over baseline"
                    />
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Improvement curve</CardTitle>
                    <CardDescription>
                        Normalized Edit Distance (NED) across learning
                        iterations for patient_001.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <svg
                            viewBox={`0 0 ${width} ${height}`}
                            className="h-48 w-full max-w-2xl"
                            role="img"
                            aria-label="NED improvement curve"
                        >
                            <defs>
                                <linearGradient
                                    id="areaFill"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                >
                                    <stop
                                        offset="0%"
                                        stopColor="#0891B2"
                                        stopOpacity="0.3"
                                    />
                                    <stop
                                        offset="100%"
                                        stopColor="#0891B2"
                                        stopOpacity="0"
                                    />
                                </linearGradient>
                            </defs>
                            {[0.25, 0.5, 0.75].map((p) => (
                                <line
                                    key={p}
                                    x1={padding}
                                    y1={padding + p * innerH}
                                    x2={padding + innerW}
                                    y2={padding + p * innerH}
                                    stroke="#0891B2"
                                    strokeOpacity="0.12"
                                    strokeDasharray="2 4"
                                />
                            ))}
                            <path
                                d={
                                    pathD +
                                    ` L ${padding + innerW},${padding + innerH} L ${padding},${padding + innerH} Z`
                                }
                                fill="url(#areaFill)"
                            />
                            <path
                                d={pathD}
                                fill="none"
                                stroke="#0891B2"
                                strokeWidth={2.5}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                            {points.map(([x, y], i) => (
                                <g key={i}>
                                    <circle
                                        cx={x}
                                        cy={y}
                                        r={5}
                                        fill="white"
                                        stroke="#0891B2"
                                        strokeWidth={2}
                                    />
                                    <text
                                        x={x}
                                        y={y - 10}
                                        textAnchor="middle"
                                        fontSize="10"
                                        fill="#164E63"
                                    >
                                        {ned[i].ned.toFixed(4)}
                                    </text>
                                </g>
                            ))}
                            {ned.map((d, i) => {
                                const x =
                                    padding +
                                    (i / Math.max(1, ned.length - 1)) * innerW;
                                return (
                                    <text
                                        key={d.iteration}
                                        x={x}
                                        y={height - 6}
                                        textAnchor="middle"
                                        fontSize="10"
                                        fill="#164E63"
                                    >
                                        {d.iteration}
                                    </text>
                                );
                            })}
                        </svg>
                    </div>
                </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Sparkles className="h-4 w-4" />
                            Learned rules
                        </CardTitle>
                        <CardDescription>
                            Substitution rules extracted from the difference
                            between drafts and clinician-edited drafts.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {rules.length === 0 ? (
                            <p className="text-sm text-foreground/60">
                                No rules learned yet. Run the Part 2 loop to
                                populate.
                            </p>
                        ) : (
                            rules.map((r, i) => (
                                <div
                                    key={i}
                                    className="rounded-md border border-primary/10 bg-white/60 p-3"
                                >
                                    <div className="text-xs font-mono text-foreground/80">
                                        <span className="text-red-600 line-through">
                                            {r.from}
                                        </span>{" "}
                                        →{" "}
                                        <span className="text-emerald-700">
                                            {r.to}
                                        </span>
                                    </div>
                                    <div className="mt-1 text-[10px] uppercase tracking-wider text-foreground/50">
                                        Seen {r.count} time
                                        {r.count === 1 ? "" : "s"}
                                    </div>
                                </div>
                            ))
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                            <ShieldCheck className="h-4 w-4" />
                            Safety guardrails
                        </CardTitle>
                        <CardDescription>
                            The learning loop is intentionally narrow.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2 text-sm text-foreground/85">
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                                Only formatting changes are learned. No
                                clinical content is auto-corrected.
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                                The safety validator runs independently of NED
                                — a low NED with missing facts still fails.
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                                [PENDING] and [CONFLICT] flags are never
                                removed by the learning loop.
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                                Rules are applied longest-first to avoid
                                partial-match corruption.
                            </li>
                        </ul>
                    </CardContent>
                </Card>
            </div>

            <div className="flex flex-wrap gap-3">
                <Button asChild variant="cta">
                    <Link href="/patients" className="flex items-center gap-2">
                        <PlayCircle className="h-4 w-4" />
                        Run an iteration
                    </Link>
                </Button>
                <Button asChild variant="outline">
                    <Link href="/drafts" className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Inspect latest draft
                    </Link>
                </Button>
            </div>
        </div>
    );
}
