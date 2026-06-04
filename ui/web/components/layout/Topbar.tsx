"use client";

import { useEffect, useState } from "react";
import { Stethoscope, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AnimatedDot } from "@/components/ui/animated-dot";
import { checkHealth } from "@/lib/api";

/**
 * Topbar — calm status pill + page context.
 *
 * Design rules followed:
 *  - Single height (64px / h-16), single border-bottom.
 *  - No glassmorphism backdrop-blur (skill §5: glassmorphism inappropriate for
 *    dashboards / clinical surfaces; it hurts legibility of the text below).
 *  - One accent color throughout. No gradient text.
 *  - Live status communicated with a single AnimatedDot, not a glowing ring.
 */
export default function Topbar() {
    const [online, setOnline] = useState<boolean | null>(null);

    useEffect(() => {
        let mounted = true;
        const ping = async () => {
            try {
                const r = await checkHealth();
                if (!mounted) return;
                setOnline(r.status === "healthy");
            } catch {
                if (!mounted) return;
                setOnline(false);
            }
        };
        ping();
        const id = setInterval(ping, 30_000);
        return () => {
            mounted = false;
            clearInterval(id);
        };
    }, []);

    const status =
        online === null ? "checking" : online ? "live" : "offline";
    const badgeVariant =
        online === null
            ? "warning"
            : online
                ? "success"
                : "danger";

    return (
        <header
            className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/90 backdrop-blur-sm px-4 md:px-6"
            role="banner"
        >
            <div className="flex items-center gap-2">
                <Stethoscope
                    className="h-4 w-4 text-primary"
                    aria-hidden="true"
                />
                <h1 className="text-sm font-semibold text-foreground">
                    Discharge Summary Agent
                </h1>
            </div>

            <div className="ml-auto flex items-center gap-3">
                <Badge
                    variant={badgeVariant}
                    size="default"
                    className="gap-1.5"
                    aria-live="polite"
                >
                    <AnimatedDot status={status} />
                    {online ? (
                        <Wifi className="h-3 w-3" aria-hidden="true" />
                    ) : (
                        <WifiOff className="h-3 w-3" aria-hidden="true" />
                    )}
                    <span>
                        {online === null
                            ? "Checking API"
                            : online
                                ? "API online"
                                : "API offline"}
                    </span>
                </Badge>
            </div>
        </header>
    );
}
