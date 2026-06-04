"use client";

import * as React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * ShimmerButton — 21st.dev-style CTA with a sweeping shimmer overlay
 * driven by Motion. Accessible, focusable, works as <button> or <a>.
 */
interface ShimmerButtonProps
    extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
    children: React.ReactNode;
    href?: string;
    variant?: "primary" | "ghost";
    icon?: React.ReactNode;
    iconRight?: React.ReactNode;
}

export const ShimmerButton = React.forwardRef<
    HTMLButtonElement,
    ShimmerButtonProps
>(function ShimmerButton(
    { children, className, href, variant = "primary", icon, iconRight, ...props },
    ref
) {
    const base =
        "group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-lg px-5 py-2.5 text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary disabled:opacity-50 disabled:pointer-events-none cursor-pointer";
    const variants = {
        primary:
            "bg-[var(--color-cta)] text-white shadow-md hover:shadow-lg hover:-translate-y-0.5",
        ghost:
            "border border-primary/30 bg-white/70 text-primary backdrop-blur hover:bg-white",
    } as const;

    const inner = (
        <>
            {icon && (
                <span className="relative z-10 flex items-center">
                    {icon}
                </span>
            )}
            <span className="relative z-10">{children}</span>
            {iconRight && (
                <span className="relative z-10 flex items-center transition-transform duration-200 group-hover:translate-x-0.5">
                    {iconRight}
                </span>
            )}
            {/* Shimmer sweep */}
            <motion.span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 skew-x-[-20deg] bg-white/30"
                animate={{ x: ["-50%", "250%"] }}
                transition={{
                    duration: 2.4,
                    repeat: Infinity,
                    ease: "easeInOut",
                    repeatDelay: 0.6,
                }}
                style={{ filter: "blur(2px)" }}
            />
        </>
    );

    if (href) {
        return (
            <a
                href={href}
                className={cn(base, variants[variant], className)}
            >
                {inner}
            </a>
        );
    }
    return (
        <button
            ref={ref}
            className={cn(base, variants[variant], className)}
            {...props}
        >
            {inner}
        </button>
    );
});

export default ShimmerButton;
