"use client";

/**
 * components/ui/glow-pulse.tsx
 *
 * 21st.dev-style "pulsing dot" used for live indicators (API health, agent
 * running, etc.). Honors prefers-reduced-motion.
 */

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

export interface GlowPulseProps {
    color?: "primary" | "success" | "warning" | "danger";
    className?: string;
    label?: string;
}

const colorMap: Record<NonNullable<GlowPulseProps["color"]>, string> = {
    primary: "bg-primary",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    danger: "bg-red-500",
};

const ringMap: Record<NonNullable<GlowPulseProps["color"]>, string> = {
    primary: "bg-primary/40",
    success: "bg-emerald-500/40",
    warning: "bg-amber-500/40",
    danger: "bg-red-500/40",
};

export function GlowPulse({
    color = "success",
    className,
    label,
}: GlowPulseProps) {
    const reduced = useReducedMotion();
    return (
        <span
            className={cn("relative inline-flex items-center", className)}
            role="status"
            aria-label={label}
        >
            {!reduced && (
                <span
                    className={cn(
                        "absolute inline-flex h-2.5 w-2.5 animate-ping rounded-full",
                        ringMap[color]
                    )}
                    aria-hidden="true"
                />
            )}
            <span
                className={cn(
                    "relative inline-flex h-2.5 w-2.5 rounded-full",
                    colorMap[color]
                )}
                aria-hidden="true"
            />
        </span>
    );
}
