"use client";

/**
 * components/ui/marquee.tsx
 *
 * 21st.dev-inspired marquee for showing inline status strips (e.g., the
 * pill row of clinical guard markers). Auto-pauses on hover and respects
 * prefers-reduced-motion.
 */

import * as React from "react";
import { useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

export interface MarqueeProps extends React.HTMLAttributes<HTMLDivElement> {
    speed?: number; // pixels per second
    pauseOnHover?: boolean;
    children: React.ReactNode;
}

export function Marquee({
    children,
    className,
    speed = 40,
    pauseOnHover = true,
    ...props
}: MarqueeProps) {
    const reduced = useReducedMotion();
    const [paused, setPaused] = React.useState(false);

    return (
        <div
            className={cn(
                "group relative flex w-full overflow-hidden",
                "[mask-image:linear-gradient(to_right,transparent,white_10%,white_90%,transparent)]",
                className
            )}
            onMouseEnter={() => pauseOnHover && setPaused(true)}
            onMouseLeave={() => pauseOnHover && setPaused(false)}
            {...props}
        >
            <div
                className="flex shrink-0 gap-6 py-2"
                style={{
                    animation:
                        reduced || paused
                            ? "none"
                            : `marquee ${Math.max(
                                4,
                                100 / speed
                            )}s linear infinite`,
                    minWidth: "100%",
                }}
            >
                {children}
            </div>
            <div
                className="flex shrink-0 gap-6 py-2"
                aria-hidden="true"
                style={{
                    animation:
                        reduced || paused
                            ? "none"
                            : `marquee ${Math.max(
                                4,
                                100 / speed
                            )}s linear infinite`,
                    minWidth: "100%",
                }}
            >
                {children}
            </div>
            <style jsx>{`
                @keyframes marquee {
                    from {
                        transform: translateX(0);
                    }
                    to {
                        transform: translateX(-100%);
                    }
                }
            `}</style>
        </div>
    );
}
