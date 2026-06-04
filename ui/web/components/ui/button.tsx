import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Dscribe Button.
 *
 * Design rules followed (taste-skill §4.5):
 *  - Solid fills, no gradient/glow.
 *  - One radius (8px, from --radius-input) for every size.
 *  - Hover: subtle color shift, NO layout shift (no translate/scale on hover).
 *  - Active: -translate-y-[1px] tactile push (single 1px shift, instant).
 *  - Focus: ring handled globally in globals.css :focus-visible.
 *  - Min height 44px for default size (a11y touch target).
 *  - Disabled = opacity 50 + pointer-events none (not cursor: not-allowed).
 */
const buttonVariants = cva(
    [
        // layout
        "inline-flex items-center justify-center gap-2 whitespace-nowrap",
        // shape (single radius system)
        "rounded-input",
        // type
        "text-sm font-medium",
        // motion (transitions only on color/bg, never on transform except active)
        "transition-colors duration-200",
        // focus handled by globals
        "focus-visible:outline-none",
        // disabled
        "disabled:pointer-events-none disabled:opacity-50",
        // cursor
        "cursor-pointer",
        // icon sizing
        "[&_svg]:size-4 [&_svg]:shrink-0",
        // tactile active (no hover translate)
        "active:translate-y-px",
    ].join(" "),
    {
        variants: {
            variant: {
                // Solid brand CTA. Highest visual weight.
                cta: "bg-cta text-cta-fg hover:bg-cta/90 shadow-sm",
                // Primary brand action.
                default: "bg-primary text-primary-fg hover:bg-primary/90",
                // Subdued (e.g. secondary actions in a row).
                secondary:
                    "bg-muted text-foreground hover:bg-muted/80 border border-border",
                // Outlined, for tertiary actions.
                outline:
                    "border border-border bg-background text-foreground hover:bg-muted",
                // No chrome at all, for inline affordances.
                ghost: "text-foreground hover:bg-muted",
                // Destructive only for truly destructive actions (delete draft etc.).
                destructive:
                    "bg-status-missing text-white hover:bg-status-missing/90",
                // Link-styled (for inline use).
                link: "text-primary underline-offset-4 hover:underline",
            },
            size: {
                sm: "h-9 px-3 text-xs rounded-input",
                default: "h-11 px-5 py-2",          // 44px touch target
                lg: "h-12 px-6 text-base rounded-input",
                icon: "h-10 w-10",                  // 40px (paired with sr-only label)
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
);

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
    asChild?: boolean;
}

import { Slot } from "@radix-ui/react-slot";

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button";
        return (
            <Comp
                className={cn(buttonVariants({ variant, size, className }))}
                ref={ref}
                {...props}
            />
        );
    }
);
Button.displayName = "Button";

export { Button, buttonVariants };
