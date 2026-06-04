"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * AuroraBackground — 21st.dev-style soft, animated aurora.
 * Three blurred blobs drifting on overlapping Motion loops.
 */
interface AuroraBackgroundProps {
    className?: string;
}

export function AuroraBackground({ className }: AuroraBackgroundProps) {
    return (
        <div
            className={cn(
                "pointer-events-none absolute inset-0 overflow-hidden",
                className
            )}
            aria-hidden="true"
        >
            <motion.div
                className="absolute -left-32 -top-24 h-[520px] w-[520px] rounded-full"
                style={{
                    background:
                        "radial-gradient(circle at center, rgba(8,145,178,0.45), transparent 65%)",
                    filter: "blur(70px)",
                }}
                animate={{
                    x: [0, 60, 0],
                    y: [0, 40, 0],
                }}
                transition={{
                    duration: 18,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute -right-32 top-10 h-[480px] w-[480px] rounded-full"
                style={{
                    background:
                        "radial-gradient(circle at center, rgba(5,150,105,0.35), transparent 65%)",
                    filter: "blur(80px)",
                }}
                animate={{
                    x: [0, -50, 0],
                    y: [0, 70, 0],
                }}
                transition={{
                    duration: 22,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute bottom-[-160px] left-1/3 h-[420px] w-[420px] rounded-full"
                style={{
                    background:
                        "radial-gradient(circle at center, rgba(34,211,238,0.30), transparent 65%)",
                    filter: "blur(70px)",
                }}
                animate={{
                    x: [0, 40, -20, 0],
                    y: [0, -30, 20, 0],
                }}
                transition={{
                    duration: 26,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
        </div>
    );
}

export default AuroraBackground;
