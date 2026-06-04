"use client";

import { useEffect, useState } from "react";
import { Activity, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { GlowPulse } from "@/components/ui/glow-pulse";
import { checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

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

    return (
        <header
            className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-primary/10 bg-white/70 backdrop-blur-md px-4 md:px-6"
            role="banner"
        >
            <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
                <h1 className="text-sm font-semibold text-primary">
                    Discharge Summary Agent
                </h1>
            </div>

            <div className="ml-auto flex items-center gap-3">
                <Badge
                    variant={online === false ? "danger" : online ? "success" : "muted"}
                    className="gap-1.5"
                    aria-live="polite"
                >
                    <GlowPulse
                        color={online === false ? "danger" : online ? "success" : "warning"}
                        className="ml-[-2px]"
                    />
                    {online ? (
                        <Wifi className="h-3 w-3" aria-hidden="true" />
                    ) : (
                        <WifiOff className="h-3 w-3" aria-hidden="true" />
                    )}
                    <span>
                        {online === null
                            ? "Checking API..."
                            : online
                                ? "API Online"
                                : "API Offline"}
                    </span>
                </Badge>
            </div>
        </header>
    );
}
