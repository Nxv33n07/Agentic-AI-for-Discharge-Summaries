"use client";

/**
 * components/ui/progress-arc.tsx
 *
 * 21st.dev-style animated progress arc. Renders a circular SVG with two
 * arcs: the track and the value, where the value arc grows from 0 to the
 * current `value` on mount/update. Respects prefers-reduced-motion.
 */

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

export interface ProgressArcProps {
    value: number; // 0..1
    size?: number; // px
    strokeWidth?: number;
    className?: string;
    label?: string;
    sublabel?: string;
    color?: string;
    trackColor?: string;
    showValue?: boolean;
}

export function ProgressArc({
    value,
    size = 96,
    strokeWidth = 8,
    className,
    label,
    sublabel,
    color = "#b2793dff",
    trackColor = "rgba(8,145,178,0.15)",
    showValue = true,
}: ProgressArcProps) {
    const reduced = useReducedMotion();
    const safe = Math.max(0, Math.min(1, value));
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - safe);

    return (
        <div
            className={cn(
                "relative inline-flex items-center justify-center",
                className
            )}
            style={{ width: size, height: size }}
            role="img"
            aria-label={
                label
                    ? `${label}: ${Math.round(safe * 100)}%`
                    : `${Math.round(safe * 100)}%`
            }
        >
            <svg width={size} height={size} className="-rotate-90">
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={trackColor}
                    strokeWidth={strokeWidth}
                    fill="none"
                />
                <motion.circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    fill="none"
                    initial={
                        reduced ? { strokeDashoffset: offset } : undefined
                    }
                    animate={{ strokeDashoffset: offset }}
                    transition={{
                        type: "spring",
                        stiffness: 80,
                        damping: 18,
                    }}
                    style={{
                        strokeDasharray: circumference,
                    }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                {showValue && (
                    <span
                        className="text-lg font-semibold text-primary tabular-nums"
                        data-testid="progress-arc-value"
                    >
                        {Math.round(safe * 100)}%
                    </span>
                )}
                {label && (
                    <span className="text-[10px] uppercase tracking-wider text-foreground/60">
                        {label}
                    </span>
                )}
                {sublabel && (
                    <span className="text-[10px] text-foreground/50">
                        {sublabel}
                    </span>
                )}
            </div>
        </div>
    );
}
