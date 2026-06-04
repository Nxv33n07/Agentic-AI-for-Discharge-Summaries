"use client";

/**
 * components/ui/spotlight-card.tsx
 *
 * 21st.dev-style "magic card": tracks pointer position and renders a soft
 * gradient that follows the cursor. Used for interactive cards and the
 * hero on the dashboard.
 */

import * as React from "react";
import {
    motion,
    useMotionTemplate,
    useMotionValue,
    useReducedMotion,
} from "motion/react";
import { cn } from "@/lib/utils";

export interface SpotlightCardProps
    extends React.HTMLAttributes<HTMLDivElement> {
    /** Spotlight color (default: cyan-tinted). */
    spotlightColor?: string;
    /** Border color for the resting state. */
    borderColor?: string;
}

export const SpotlightCard = React.forwardRef<
    HTMLDivElement,
    SpotlightCardProps
>(
    (
        {
            className,
            children,
            spotlightColor = "rgba(8, 145, 178, 0.18)",
            ...props
        },
        ref
    ) => {
        const reduced = useReducedMotion();
        const x = useMotionValue(0);
        const y = useMotionValue(0);

        const transform = useMotionTemplate`translateX(${x}px) translateY(${y}px)`;

        const handleMove = (
            e: React.MouseEvent<HTMLDivElement, MouseEvent>
        ) => {
            if (reduced) return;
            const rect = e.currentTarget.getBoundingClientRect();
            x.set(e.clientX - rect.left - 200);
            y.set(e.clientY - rect.top - 200);
        };

        return (
            <div
                ref={ref}
                onMouseMove={handleMove}
                className={cn(
                    "group relative overflow-hidden rounded-xl border border-primary/10 bg-white/70 backdrop-blur-sm shadow-sm",
                    "transition-shadow duration-200 hover:shadow-md",
                    className
                )}
                {...props}
            >
                {!reduced && (
                    <motion.div
                        aria-hidden="true"
                        className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                        style={{
                            background: `radial-gradient(400px circle at ${transform.get()}, ${spotlightColor}, transparent 60%)`,
                        }}
                    />
                )}
                <div className="relative">{children}</div>
            </div>
        );
    }
);
SpotlightCard.displayName = "SpotlightCard";
