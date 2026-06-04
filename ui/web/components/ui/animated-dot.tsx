"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * AnimatedDot — a single, calm pulsing dot for live-status indicators.
 *
 * Replaces the more elaborate GlowPulse. The old component used a multi-layered
 * radial gradient + box-shadow ring, which read as decorative AI-default.
 *
 * Design rules followed (taste-skill §5 + §6.B):
 *  - One single dot. No outer ring, no extra glow.
 *  - Animation: opacity 1 → 0.4 → 1 over 2s, ease-in-out, infinite.
 *  - Honors prefers-reduced-motion (collapses to a static dot).
 *  - One accent color per status: cta (live), warning (checking), danger (offline).
 *  - Width 8px, height 8px — same size regardless of status.
 */
export interface AnimatedDotProps
    extends React.HTMLAttributes<HTMLSpanElement> {
    status?: "live" | "checking" | "offline";
}

const STATUS_COLOR: Record<NonNullable<AnimatedDotProps["status"]>, string> = {
    live: "bg-cta",
    checking: "bg-status-pending",
    offline: "bg-status-missing",
};

export function AnimatedDot({
    status = "live",
    className,
    ...props
}: AnimatedDotProps) {
    return (
        <span
            role="presentation"
            aria-hidden="true"
            className={cn(
                "relative inline-block h-2 w-2 rounded-full",
                STATUS_COLOR[status],
                // Animation is auto-collapsed by the prefers-reduced-motion guard
                // in globals.css. This class only animates when motion is allowed.
                "motion-safe:animate-pulse-soft",
                className
            )}
            {...props}
        />
    );
}
