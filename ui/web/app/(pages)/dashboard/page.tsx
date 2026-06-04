"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import {
    Activity,
    ArrowRight,
    Brain,
    CheckCircle2,
    FileText,
    ShieldCheck,
    Sparkles,
    Stethoscope,
    Users,
    Zap,
} from "lucide-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { ProgressArc } from "@/components/ui/progress-arc";
import { AnimatedDot } from "@/components/ui/animated-dot";
import { Button } from "@/components/ui/button";
import { StaggerContainer, StaggerItem } from "@/components/layout/StaggerContainer";
import { checkHealth, getDraft } from "@/lib/api";
import { KNOWN_PATIENTS } from "@/lib/patients";

const STAT_CARDS = [
    {
        icon: Users,
        label: "Patients Available",
        value: KNOWN_PATIENTS.length,
        accent: "text-primary",
    },
    {
        icon: FileText,
        label: "Required Sections",
        value: 11,
        accent: "text-primary",
    },
    {
        icon: Activity,
        label: "Tool Calls / Run",
        value: 18,
        accent: "text-primary",
    },
    {
        icon: ShieldCheck,
        label: "Guardrail Layers",
        value: 3,
        accent: "text-[var(--color-cta)]",
    },
] as const;

const GUARD_MARKERS = [
    "[MISSING]",
    "[PENDING]",
    "[CONFLICT]",
    "[NOT DOCUMENTED]",
    "[UNCLEAR — OCR]",
    "[REVIEW]",
];

const FEATURE_CARDS = [
    {
        title: "Transparent ReAct Loop",
        description:
            "Step-by-step reasoning with tool calls visible in the observability trace.",
        icon: Activity,
        href: "/trace",
        cta: "Open trace viewer",
    },
    {
        title: "Three-Layer No-Fabrication",
        description:
            "Prompt rules, fact status tagging, and an output validator. Every missing field is explicitly labeled.",
        icon: ShieldCheck,
        href: "/patients",
        cta: "Run a guarded patient",
    },
    {
        title: "Part 2 Learning Loop",
        description:
            "Improves from clinician edits using NED reward and substitution rules. Always safety-validated.",
        icon: Brain,
        href: "/learning",
        cta: "See improvement curve",
    },
] as const;

const REQUIREMENT_HIGHLIGHTS = [
    { label: "Real agent loop", met: true },
    { label: "PDF ingestion", met: true },
    { label: "No fabrication guardrail", met: true },
    { label: "Medication reconciliation", met: true },
    { label: "Conflict handling", met: true },
    { label: "Tool use (15 tools)", met: true },
    { label: "Robust failure handling", met: true },
    { label: "Hard iteration cap (12)", met: true },
    { label: "Observability trace", met: true },
];

const fadeUp = {
    hidden: { opacity: 0, y: 16 },
    show: (i: number) => ({
        opacity: 1,
        y: 0,
        transition: {
            delay: 0.08 * i,
            duration: 0.5,
            ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
        },
    }),
};

export default function DashboardPage() {
    const [apiOnline, setApiOnline] = useState<boolean | null>(null);

    const [patients, setPatients] = useState(KNOWN_PATIENTS);

    useEffect(() => {
        checkHealth()
            .then(() => setApiOnline(true))
            .catch(() => setApiOnline(false));

        Promise.all(
            KNOWN_PATIENTS.map(async (p) => {
                try {
                    await getDraft(p.id);
                    return { ...p, status: "draft-available" as const };
                } catch {
                    return p;
                }
            })
        ).then(setPatients);
    }, []);

    return (
        <div className="space-y-8" data-testid="dashboard-page">
            {/* ============================== HERO ============================== */}
            <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="relative overflow-hidden rounded-card border border-border bg-card shadow-sm"
            >

                {/* Decorative floating icons */}
                <motion.div
                    aria-hidden="true"
                    className="pointer-events-none absolute right-8 top-8 hidden md:block text-primary/15"
                    animate={{ y: [0, -10, 0], rotate: [0, 4, 0] }}
                    transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                >
                    <Stethoscope className="h-24 w-24" />
                </motion.div>
                <motion.div
                    aria-hidden="true"
                    className="pointer-events-none absolute right-40 bottom-6 hidden md:block text-emerald-500/20"
                    animate={{ y: [0, 8, 0], rotate: [0, -3, 0] }}
                    transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
                >
                    <ShieldCheck className="h-16 w-16" />
                </motion.div>

                <div className="relative z-10 p-6 md:p-10">
                    <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                        <div className="max-w-2xl space-y-4">
                            {/* Top badges */}
                            <motion.div
                                custom={0}
                                initial="hidden"
                                animate="show"
                                variants={fadeUp}
                                className="flex flex-wrap items-center gap-2"
                            >
                                <Badge variant="default">Healthcare · v0.1</Badge>
                                <Badge
                                    variant={
                                        apiOnline === false
                                            ? "danger"
                                            : apiOnline
                                                ? "success"
                                                : "muted"
                                    }
                                    className="gap-1.5"
                                >
                                    <AnimatedDot
                                        status={
                                            apiOnline === false
                                                ? "offline"
                                                : apiOnline
                                                    ? "live"
                                                    : "checking"
                                        }
                                    />
                                    {apiOnline === null
                                        ? "Pinging..."
                                        : apiOnline
                                            ? "API Ready"
                                            : "API Offline"}
                                </Badge>
                                <Badge variant="outline" className="gap-1">
                                    <Sparkles className="h-3 w-3" />
                                    21st.dev · Framer Motion
                                </Badge>
                            </motion.div>

                            {/* Headline */}
                            <motion.h1
                                custom={1}
                                initial="hidden"
                                animate="show"
                                variants={fadeUp}
                                className="text-3xl font-bold leading-tight md:text-4xl lg:text-5xl text-foreground"
                            >
                                <span>Agentic Discharge</span>
                                <br />
                                <span>Summaries, </span>
                                <span className="text-primary">drafted safely.</span>
                            </motion.h1>

                            {/* Sub */}
                            <motion.p
                                custom={2}
                                initial="hidden"
                                animate="show"
                                variants={fadeUp}
                                className="max-w-xl text-sm leading-relaxed text-foreground/75 md:text-base"
                            >
                                Dscribe reads raw clinical PDFs through a transparent
                                ReAct loop, applies a three-layer no-fabrication
                                guardrail, and drafts a discharge summary for
                                clinician review. Every fact is sourced — never
                                invented.
                            </motion.p>

                            {/* CTAs */}
                            <motion.div
                                custom={3}
                                initial="hidden"
                                animate="show"
                                variants={fadeUp}
                                className="flex flex-wrap gap-3 pt-1"
                            >
                                <Button asChild variant="cta" size="lg" className="gap-2">
                                    <Link href="/patients">
                                        <Zap className="h-4 w-4" />
                                        Start an Agent Run
                                        <ArrowRight className="h-4 w-4" />
                                    </Link>
                                </Button>
                                <Button asChild variant="outline" size="lg" className="gap-2">
                                    <Link href="/learning">
                                        <Brain className="h-4 w-4" />
                                        View Learning Loop
                                    </Link>
                                </Button>
                            </motion.div>
                        </div>

                        {/* Right-side status stack */}
                        <motion.div
                            custom={4}
                            initial="hidden"
                            animate="show"
                            variants={fadeUp}
                            className="hidden md:flex flex-col items-end gap-3"
                        >
                            <ProgressArc
                                value={0.94}
                                size={130}
                                strokeWidth={10}
                                color="#059669"
                                label="Safe"
                                sublabel="guarded runs"
                            />
                            <div className="flex items-center gap-2 rounded-full border border-primary/20 bg-white/70 px-3 py-1.5 text-xs text-foreground/70 backdrop-blur">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                Live · 15 tools · 12-step cap
                            </div>
                        </motion.div>
                    </div>
                </div>
            </motion.section>



            {/* ============================== STATS ============================== */}
            <StaggerContainer className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {STAT_CARDS.map((s) => {
                    const Icon = s.icon;
                    return (
                        <StaggerItem key={s.label}>
                            <motion.div
                                whileHover={{ y: -4 }}
                                transition={{
                                    duration: 0.2,
                                    ease: "easeOut",
                                }}
                            >
                                <Card className="h-full transition-shadow hover:shadow-md">
                                    <CardContent className="flex items-center gap-3 p-5">
                                        <div
                                            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 ${s.accent}`}
                                        >
                                            <Icon
                                                className="h-5 w-5"
                                                aria-hidden="true"
                                            />
                                        </div>
                                        <div className="leading-tight">
                                            <div className="text-2xl font-bold text-primary">
                                                <AnimatedCounter value={s.value} />
                                            </div>
                                            <div className="text-xs text-foreground/60">
                                                {s.label}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        </StaggerItem>
                    );
                })}
            </StaggerContainer>

            {/* ============================== FEATURE CARDS ============================== */}
            <StaggerContainer className="grid gap-4 md:grid-cols-3">
                {FEATURE_CARDS.map((f) => {
                    const Icon = f.icon;
                    return (
                        <StaggerItem key={f.title}>
                            <motion.div
                                whileHover={{ y: -4 }}
                                transition={{ duration: 0.2, ease: "easeOut" }}
                                className="h-full"
                            >
                                <Card
                                    className="h-full"
                                    interactive
                                >
                                    <div className="p-5">
                                        <div className="mb-3 flex items-center gap-2">
                                            <span className="flex h-9 w-9 items-center justify-center rounded-input bg-primary/10 text-primary">
                                                <Icon className="h-4 w-4" />
                                            </span>
                                            <h3 className="text-base font-semibold text-foreground">
                                                {f.title}
                                            </h3>
                                        </div>
                                        <p className="text-sm leading-relaxed text-muted-foreground">
                                            {f.description}
                                        </p>
                                        <Link
                                            href={f.href}
                                            className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                                        >
                                            {f.cta}
                                            <ArrowRight className="h-3.5 w-3.5" />
                                        </Link>
                                    </div>
                                </Card>
                            </motion.div>
                        </StaggerItem>
                    );
                })}
            </StaggerContainer>

            {/* ============================== PATIENTS ============================== */}
            <section>
                <div className="mb-3 flex items-end justify-between">
                    <h2 className="text-lg font-semibold text-primary">
                        Available Patients
                    </h2>
                    <Link
                        href="/patients"
                        className="text-xs font-medium text-primary/80 hover:text-primary"
                    >
                        View all →
                    </Link>
                </div>
                <StaggerContainer className="grid gap-3 md:grid-cols-2">
                    {patients.map((p) => (
                        <StaggerItem key={p.id}>
                            <motion.div
                                whileHover={{ y: -3, scale: 1.01 }}
                                transition={{ duration: 0.2, ease: "easeOut" }}
                            >
                                <Card className="cursor-pointer transition-colors hover:border-primary/40 hover:shadow-md">
                                    <CardContent className="p-5">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <div className="text-sm font-semibold text-primary">
                                                    {p.name}
                                                </div>
                                                <div className="text-xs text-foreground/60">
                                                    {p.id} · {p.age ?? "?"}y{" "}
                                                    {p.gender ?? ""}
                                                    {p.admitted
                                                        ? ` · admitted ${p.admitted}`
                                                        : ""}
                                                </div>
                                            </div>
                                            <Badge variant="outline">
                                                {p.status}
                                            </Badge>
                                        </div>
                                        <p className="mt-2 text-sm text-foreground/80">
                                            {p.summary}
                                        </p>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        </StaggerItem>
                    ))}
                </StaggerContainer>
            </section>
        </div>
    );
}
