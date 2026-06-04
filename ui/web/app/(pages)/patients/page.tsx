"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
    ArrowRight,
    PlayCircle,
    Stethoscope,
    Users,
} from "lucide-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { AnimatedDot } from "@/components/ui/animated-dot";
import { StaggerContainer, StaggerItem } from "@/components/layout/StaggerContainer";
import { KNOWN_PATIENTS, getPatientInfo } from "@/lib/patients";
import { useAgentRun } from "@/lib/useAgentRun";

export default function PatientsPage() {
    const [patientId, setPatientId] = useState<string>(KNOWN_PATIENTS[0].id);
    const [enableLearning, setEnableLearning] = useState<boolean>(false);

    const successCardRef = useRef<HTMLDivElement | null>(null);
    const { status, error, result, run } = useAgentRun();

    const current = getPatientInfo(patientId);
    const running = status === "running";

    const onRun = async () => {
        try {
            await run(patientId);

        } catch {
            // surfaced via status/error
        }
    };

    return (
        <div className="space-y-6" data-testid="patients-page">
            <header className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <Users
                        className="h-4 w-4 text-primary"
                        aria-hidden="true"
                    />
                    <h1 className="text-2xl font-bold text-primary">
                        Run the Agent
                    </h1>
                    {running && (
                        <span className="ml-2 inline-flex items-center gap-1.5 text-xs text-foreground/60">
                            <AnimatedDot status="checking" />
                            Agent is reasoning...
                        </span>
                    )}
                </div>
                <p className="text-sm text-foreground/70">
                    Select a patient and trigger the ReAct agent. The draft
                    and trace are produced via the FastAPI backend.
                </p>
            </header>

            <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
                <Card>
                    <CardHeader>
                        <CardTitle>Run configuration</CardTitle>
                        <CardDescription>
                            Settings for this agent invocation.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="patient-input">Patient ID</Label>
                            <Input
                                id="patient-input"
                                value={patientId}
                                onChange={(e) => setPatientId(e.target.value)}
                                disabled={running}
                                placeholder="Enter patient ID (e.g., patient_001)"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Learning loop</Label>
                            <div className="rounded-md border border-primary/10 bg-white/60 p-3">
                                <Switch
                                    checked={enableLearning}
                                    onChange={(e) =>
                                        setEnableLearning(e.target.checked)
                                    }
                                    disabled={running}
                                    label="Enable Learning Improver"
                                    description="Apply substitution rules learned from prior clinician edits."
                                />
                            </div>
                        </div>

                        <div className="pt-2">
                            <Button
                                variant="cta"
                                size="lg"
                                className="w-full"
                                onClick={onRun}
                                disabled={running}
                                aria-label="Run Agent"
                                data-testid="run-agent-btn"
                            >
                                {running ? (
                                    <Spinner
                                        size="sm"
                                        label="Running agent..."
                                    />
                                ) : (
                                    <>
                                        <PlayCircle className="h-4 w-4" />
                                        Run Agent
                                    </>
                                )}
                            </Button>
                        </div>

                        {error && (
                            <Alert variant="danger">
                                <AlertTitle>Run failed</AlertTitle>
                                <AlertDescription>
                                    {error}
                                </AlertDescription>
                            </Alert>
                        )}

                        <div
                            ref={successCardRef}
                            className="relative overflow-hidden"
                        >
                            {status === "success" && result && (
                                <>
                                    <Alert
                                        variant="success"
                                        icon={
                                            <Stethoscope className="h-4 w-4" />
                                        }
                                    >
                                        <AlertTitle>Draft generated</AlertTitle>
                                        <AlertDescription>
                                            <span data-testid="success-banner">
                                                Discharge summary ready for
                                                review.
                                            </span>
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                <Button asChild size="sm">
                                                    <Link
                                                        href={`/drafts/${result.patientId}`}
                                                        className="flex items-center gap-1"
                                                    >
                                                        Review draft
                                                        <ArrowRight className="h-3.5 w-3.5" />
                                                    </Link>
                                                </Button>
                                                <Button
                                                    asChild
                                                    size="sm"
                                                    variant="outline"
                                                >
                                                    <Link
                                                        href={`/trace/${result.patientId}`}
                                                        className="flex items-center gap-1"
                                                    >
                                                        View trace
                                                        <ArrowRight className="h-3.5 w-3.5" />
                                                    </Link>
                                                </Button>
                                            </div>
                                        </AlertDescription>
                                    </Alert>
                                </>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Patient detail</CardTitle>
                        <CardDescription>
                            Snapshot of the selected patient.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {current ? (
                            <StaggerContainer className="space-y-4">
                                <StaggerItem>
                                    <div>
                                        <div className="text-xs uppercase tracking-wide text-foreground/50">
                                            Name
                                        </div>
                                        <div className="text-base font-semibold text-primary">
                                            {current.name}
                                        </div>
                                    </div>
                                </StaggerItem>
                                <StaggerItem>
                                    <div className="grid grid-cols-3 gap-3 text-sm">
                                        <div>
                                            <div className="text-xs uppercase tracking-wide text-foreground/50">
                                                ID
                                            </div>
                                            <div className="font-mono">
                                                {current.id}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs uppercase tracking-wide text-foreground/50">
                                                Age / Sex
                                            </div>
                                            <div>
                                                {current.age ?? "?"}y{" "}
                                                {current.gender ?? "-"}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs uppercase tracking-wide text-foreground/50">
                                                Admitted
                                            </div>
                                            <div>
                                                {current.admitted ?? "-"}
                                            </div>
                                        </div>
                                    </div>
                                </StaggerItem>
                                <StaggerItem>
                                    <div>
                                        <div className="text-xs uppercase tracking-wide text-foreground/50">
                                            Case summary
                                        </div>
                                        <p className="mt-1 text-sm text-foreground/80">
                                            {current.summary}
                                        </p>
                                    </div>
                                </StaggerItem>
                                <StaggerItem>
                                    <div className="flex flex-wrap gap-2">
                                        <Badge variant="default">
                                            Source: clinical PDF
                                        </Badge>
                                        <Badge variant="outline">
                                            OCR: Tesseract
                                        </Badge>
                                        <Badge variant="muted">
                                            Guarded: 3 layers
                                        </Badge>
                                    </div>
                                </StaggerItem>
                            </StaggerContainer>
                        ) : (
                            <p className="text-sm text-foreground/60">
                                Using custom patient ID: <strong>{patientId}</strong>.
                                Make sure the required files exist in the backend.
                            </p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
