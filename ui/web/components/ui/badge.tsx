import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
    "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
    {
        variants: {
            variant: {
                default: "border-transparent bg-primary text-white",
                secondary: "border-transparent bg-secondary/30 text-primary",
                success:
                    "border-transparent bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
                warning:
                    "border-transparent bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
                danger: "border-transparent bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
                info: "border-transparent bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200",
                outline: "border-primary/30 text-primary bg-primary/5",
                muted: "border-transparent bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
);

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants({ variant }), className)} {...props} />
    );
}

export { Badge, badgeVariants };
