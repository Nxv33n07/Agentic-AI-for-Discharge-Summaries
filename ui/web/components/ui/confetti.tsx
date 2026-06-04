"use client";

/**
 * components/ui/confetti.tsx
 *
 * Tiny confetti burst for success moments (e.g., draft generated, learning
 * improvement). Pure CSS — no third-party confetti lib. Respects reduced
 * motion (renders a single fade-in if reduced is preferred).
 */

import * as React from "react";
import { useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

const COLORS = [
    "#0891B2",
    "#22D3EE",
    "#059669",
    "#F59E0B",
    "#EC4899",
    "#6366F1",
];

export interface ConfettiProps {
    count?: number;
    durationMs?: number;
    className?: string;
    /** Stable seed so re-mounts don't always look identical. */
    seed?: string;
}

function hashSeed(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
        h = (h << 5) - h + s.charCodeAt(i);
        h |= 0;
    }
    return Math.abs(h);
}

export function Confetti({
    count = 24,
    durationMs = 1400,
    className,
    seed = "dscribe",
}: ConfettiProps) {
    const reduced = useReducedMotion();
    const base = React.useMemo(() => hashSeed(seed), [seed]);

    if (reduced) return null;

    const pieces = Array.from({ length: count }, (_, i) => {
        const left = ((base + i * 37) % 100);
        const delay = ((base + i * 13) % 600) / 1000;
        const rotate = ((base + i * 53) % 360);
        const size = 6 + ((base + i) % 6);
        const color = COLORS[(i + base) % COLORS.length];
        return (
            <span
                key={i}
                className="confetti-piece"
                style={{
                    left: `${left}%`,
                    backgroundColor: color,
                    width: `${size}px`,
                    height: `${size * 1.6}px`,
                    transform: `rotate(${rotate}deg)`,
                    animationDelay: `${delay}s`,
                    animationDuration: `${durationMs}ms`,
                }}
            />
        );
    });

    return (
        <div
            className={cn(
                "pointer-events-none absolute inset-0 overflow-hidden",
                className
            )}
            aria-hidden="true"
        >
            {pieces}
            <style jsx>{`
                .confetti-piece {
                    position: absolute;
                    top: -12px;
                    border-radius: 2px;
                    animation-name: confettiFall;
                    animation-timing-function: cubic-bezier(0.2, 0.7, 0.4, 1);
                    animation-fill-mode: forwards;
                }
                @keyframes confettiFall {
                    0% {
                        transform: translateY(0) rotate(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translateY(120%) rotate(720deg);
                        opacity: 0;
                    }
                }
            `}</style>
        </div>
    );
}
