"use client";

/**
 * components/ui/animated-counter.tsx
 *
 * 21st.dev-inspired number ticker. Animates from a previous value to a new
 * value over a short duration. Uses motion's animate() under the hood and
 * respects prefers-reduced-motion (we skip the animation in that case).
 */

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";

export interface AnimatedCounterProps {
    value: number;
    duration?: number;
    decimals?: number;
    prefix?: string;
    suffix?: string;
    className?: string;
    format?: (n: number) => string;
}

export function AnimatedCounter({
    value,
    duration = 0.9,
    decimals = 0,
    prefix = "",
    suffix = "",
    className,
    format,
}: AnimatedCounterProps) {
    const reduced = useReducedMotion();
    const [display, setDisplay] = useState<number>(value);
    const prev = useRef<number>(value);

    useEffect(() => {
        if (reduced) {
            setDisplay(value);
            prev.current = value;
            return;
        }
        const controls = animate(prev.current, value, {
            duration,
            ease: "easeOut",
            onUpdate: (v) => setDisplay(v),
        });
        prev.current = value;
        return () => controls.stop();
    }, [value, duration, reduced]);

    const text = format
        ? format(display)
        : `${prefix}${display.toFixed(decimals)}${suffix}`;

    return (
        <span
            className={className}
            aria-live="polite"
            data-testid="animated-counter"
        >
            {text}
        </span>
    );
}
