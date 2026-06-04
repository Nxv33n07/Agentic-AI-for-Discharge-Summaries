"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    Clipboard,
    Download,
    FileText,
    RefreshCw,
    TriangleAlert,
} from "lucide-react";
import {
    Card,
    CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Alert,
    AlertDescription,
    AlertTitle,
} from "@/components/ui/alert";
import MarkdownView from "@/components/markdown/MarkdownView";
import { getDraft } from "@/lib/api";
import { getPatientInfo, KNOWN_PATIENTS } from "@/lib/patients";

/**
 * Discharge Summary page (the page shown in the original screenshot).
 *
 * Design rules followed:
 *  - No AuroraBackground, no GridPattern, no SpotlightCard, no ShimmerButton.
 *  - Status communicated with a single Banner above the draft (not a paper
 *    confetti, not a glow).
 *  - Buttons: solid fills, calm.
 *  - Single accent color throughout.
 *  - Honest empty / loading / error states.
 *  - No "V0.6 / BETA" or similar version-label hero (per taste-skill §9.F).
 *  - No em-dashes anywhere (per taste-skill §9.G).
 */
export default function DraftDetailPage() {
    const params = useParams<{ patientId: string }>();
    const router = useRouter();
    const patientId = params?.patientId ?? "";
    const info = getPatientInfo(patientId);
    const [draft, setDraft] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [copied, setCopied] = useState(false);

    const valid = KNOWN_PATIENTS.some((p) => p.id === patientId);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const d = await getDraft(patientId);
            setDraft(d);
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Unknown error";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (valid) load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [patientId]);

    const onCopy = async () => {
        if (!draft) return;
        try {
            await navigator.clipboard.writeText(draft);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch {
            /* noop */
        }
    };

    const onDownload = () => {
        if (!draft) return;
        const blob = new Blob([draft], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${patientId}-draft.md`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    if (!valid) {
        return (
            <Card className="max-w-lg mx-auto mt-12">
                <CardContent className="p-8 text-center">
                    <p className="text-sm text-muted-foreground">
                        Unknown patient id: {patientId}
                    </p>
                    <Button asChild className="mt-4" variant="outline">
                        <Link href="/drafts">Back to drafts</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6" data-testid="draft-detail">
            {/* Page header */}
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push("/drafts")}
                        aria-label="Back to drafts"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Back
                    </Button>
                    <div>
                        <div className="flex items-center gap-2">
                            <FileText
                                className="h-4 w-4 text-primary"
                                aria-hidden="true"
                            />
                            <h1 className="text-xl font-semibold text-foreground">
                                {info?.name ?? patientId}
                            </h1>
                            <Badge variant="outline" size="sm">
                                {patientId}
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Discharge summary draft
                        </p>
                    </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={load}
                        disabled={loading}
                    >
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onCopy}
                        disabled={!draft}
                    >
                        <Clipboard className="h-4 w-4" />
                        {copied ? "Copied" : "Copy"}
                    </Button>
                    <Button
                        variant="cta"
                        size="sm"
                        onClick={onDownload}
                        disabled={!draft}
                    >
                        <Download className="h-4 w-4" />
                        Download
                    </Button>
                    <Button asChild size="sm" variant="outline">
                        <Link href={`/trace/${patientId}`}>
                            View trace
                        </Link>
                    </Button>
                </div>
            </div>

            {/* Error state */}
            {error && (
                <Alert variant="danger" icon={<TriangleAlert className="h-4 w-4" />}>
                    <AlertTitle>Could not load draft</AlertTitle>
                    <AlertDescription>
                        {error}. Run the agent from the{" "}
                        <Link
                            href="/patients"
                            className="underline font-medium"
                        >
                            Patients page
                        </Link>{" "}
                        to generate one.
                    </AlertDescription>
                </Alert>
            )}

            {/* Loading skeleton (matches the final draft shape, per taste-skill §4.5) */}
            {loading && !draft && !error && (
                <div className="space-y-3">
                    <Skeleton className="h-8 w-2/3" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-32 w-full" />
                </div>
            )}

            {/* Draft */}
            {draft && <MarkdownView content={draft} />}
        </div>
    );
}
