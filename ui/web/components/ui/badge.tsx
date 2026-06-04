import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Dscribe Badge.
 *
 * Design rules followed:
 *  - Single radius system: full pill (radius-pill = 9999px).
 *  - Tinted background + tinted foreground, never a solid accent fill.
 *  - Two sizes: sm (compact, inline) and default (table cells, status chips).
 *  - Variants map to the same status taxonomy used in MarkdownView:
 *    missing | pending | conflict | unclear | not-documented | info | success | neutral.
 */
const badgeVariants = cva(
    [
        "inline-flex items-center gap-1 rounded-pill border px-2 py-0.5",
        "text-[11px] font-medium leading-none",
        "transition-colors duration-200",
    ].join(" "),
    {
        variants: {
            variant: {
                // Default / info: cyan-tinted
                default: "border-transparent bg-primary/10 text-primary",
                // Success: emerald-tinted
                success: "border-transparent bg-cta/10 text-cta",
                // Warning: amber-tinted
                warning: "border-transparent bg-status-pending/10 text-status-pending",
                // Danger / missing: red-tinted
                danger:
                    "border-transparent bg-status-missing/10 text-status-missing",
                // Conflict: orange-tinted
                conflict:
                    "border-transparent bg-status-conflict/10 text-status-conflict",
                // Unclear: yellow-tinted
                unclear:
                    "border-transparent bg-status-unclear/10 text-status-unclear",
                // Not documented: slate-tinted
                muted: "border-transparent bg-muted text-muted-foreground",
                // Outlined neutral
                outline: "border-border text-foreground bg-background",
            },
            size: {
                sm: "text-[10px] px-1.5 py-0",
                default: "",
                lg: "text-xs px-2.5 py-1",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
);

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, size, ...props }: BadgeProps) {
    return (
        <div
            className={cn(badgeVariants({ variant, size }), className)}
            {...props}
        />
    );
}

export { Badge, badgeVariants };
