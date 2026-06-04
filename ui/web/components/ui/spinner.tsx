import * as React from "react";
import { cn } from "@/lib/utils";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
    size?: "sm" | "md" | "lg";
    label?: string;
}

const sizeMap = {
    sm: "h-4 w-4 border-2",
    md: "h-6 w-6 border-2",
    lg: "h-10 w-10 border-4",
};

function Spinner({ className, size = "md", label, ...props }: SpinnerProps) {
    return (
        <div
            role="status"
            aria-live="polite"
            className={cn("inline-flex items-center gap-3", className)}
            {...props}
        >
            <span
                className={cn(
                    "inline-block animate-spin rounded-full border-primary/30 border-t-primary",
                    sizeMap[size]
                )}
                aria-hidden="true"
            />
            {label && (
                <span className="text-sm text-foreground/70">{label}</span>
            )}
            <span className="sr-only">Loading…</span>
        </div>
    );
}

export { Spinner };
