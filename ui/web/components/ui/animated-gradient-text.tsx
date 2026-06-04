"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * AnimatedGradientText — text with an animated, shimmering gradient
 * that loops through hue positions (Motion-driven background-position).
 */
interface AnimatedGradientTextProps {
    children: React.ReactNode;
    className?: string;
    from?: string;
    via?: string;
    to?: string;
}

export function AnimatedGradientText({
    children,
    className,
    from = "#0891B2",
    via = "#22D3EE",
    to = "#059669",
}: AnimatedGradientTextProps) {
    return (
        <motion.span
            className={cn(
                "inline-block bg-clip-text text-transparent",
                className
            )}
            style={{
                backgroundImage: `linear-gradient(90deg, ${from}, ${via}, ${to}, ${from})`,
                backgroundSize: "200% 100%",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
            }}
            animate={{
                backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
            }}
            transition={{
                duration: 6,
                repeat: Infinity,
                ease: "linear",
            }}
        >
            {children}
        </motion.span>
    );
}

export default AnimatedGradientText;
