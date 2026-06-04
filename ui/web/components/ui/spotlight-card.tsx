"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * SpotlightCard — DEPRECATED for clinical / product surfaces.
 *
 * The original used a radial gradient that tracked the mouse over each
 * card. That's a "spotlight border" decoration which taste-skill §5
 * explicitly calls out as a Tell when applied broadly. We've removed it
 * from the Discharge Summary and Patient pages.
 *
 * This module now renders a plain Card so existing imports keep working.
 * For new code, just use `import { Card } from "@/components/ui/card"`.
 */
export interface SpotlightCardProps
    extends React.HTMLAttributes<HTMLDivElement> {
    interactive?: boolean;
}

export function SpotlightCard({
    className,
    interactive = false,
    ...props
}: SpotlightCardProps) {
    return (
        <div
            className={cn(
                "rounded-card border border-border bg-card text-card-foreground shadow-sm",
                "transition-colors duration-200",
                interactive && "cursor-pointer hover:border-primary/40",
                className
            )}
            {...props}
        />
    );
}

export default SpotlightCard;
