"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * AnimatedGridPattern — 21st.dev-style dotted background with
 * a soft radial highlight that drifts on a slow Motion loop.
 */
interface GridPatternProps {
    className?: string;
    dotColor?: string;
    highlightColor?: string;
    size?: number;
}

export function GridPattern({
    className,
    dotColor = "rgba(8, 145, 178, 0.18)",
    highlightColor = "rgba(34, 211, 238, 0.45)",
    size = 32,
}: GridPatternProps) {
    return (
        <div
            className={cn(
                "pointer-events-none absolute inset-0 overflow-hidden",
                className
            )}
            aria-hidden="true"
        >
            <div
                className="absolute inset-0"
                style={{
                    backgroundImage: `radial-gradient(circle, ${dotColor} 1px, transparent 1px)`,
                    backgroundSize: `${size}px ${size}px`,
                    maskImage:
                        "radial-gradient(ellipse 60% 50% at 50% 35%, #000 40%, transparent 100%)",
                    WebkitMaskImage:
                        "radial-gradient(ellipse 60% 50% at 50% 35%, #000 40%, transparent 100%)",
                }}
            />
            <motion.div
                className="absolute left-1/2 top-1/3 h-[420px] w-[420px] -translate-x-1/2 rounded-full"
                style={{
                    background: `radial-gradient(circle, ${highlightColor} 0%, transparent 70%)`,
                    filter: "blur(40px)",
                }}
                animate={{
                    x: ["-12%", "12%", "-12%"],
                    y: ["-6%", "6%", "-6%"],
                    scale: [1, 1.08, 1],
                }}
                transition={{
                    duration: 12,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
        </div>
    );
}

export default GridPattern;
