import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Dscribe Alert.
 *
 * Design rules followed:
 *  - Tinted background + tinted foreground (no solid accent fill).
 *  - Uses the same status taxonomy as Badge so colors are locked across the app.
 *  - Inline (not floating) by default; positioned in document flow.
 *  - role="alert" for screen-reader announcement.
 *  - No toast, no overlay, no close-X by default (caller opts in).
 */
const alertVariants = cva(
    [
        "relative w-full rounded-card border px-4 py-3",
        // icon layout: absolute icon at top-left, content shifted right
        "[&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:h-5 [&>svg]:w-5",
        "[&>svg~*]:pl-7",
    ].join(" "),
    {
        variants: {
            variant: {
                default: "bg-primary/5 border-primary/20 text-foreground [&>svg]:text-primary",
                info: "bg-primary/5 border-primary/20 text-foreground [&>svg]:text-primary",
                success: "bg-cta/5 border-cta/20 text-foreground [&>svg]:text-cta",
                warning: "bg-status-pending/5 border-status-pending/20 text-foreground [&>svg]:text-status-pending",
                danger: "bg-status-missing/5 border-status-missing/20 text-foreground [&>svg]:text-status-missing",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
);

export interface AlertProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
    icon?: React.ReactNode;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
    ({ className, variant, icon, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                role="alert"
                className={cn(alertVariants({ variant }), className)}
                {...props}
            >
                {icon}
                <div>{children}</div>
            </div>
        );
    }
);
Alert.displayName = "Alert";

const AlertTitle = React.forwardRef<
    HTMLHeadingElement,
    React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
    <h5
        ref={ref}
        className={cn("mb-1 text-sm font-semibold leading-snug", className)}
        {...props}
    />
));
AlertTitle.displayName = "AlertTitle";

const AlertDescription = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn("text-sm text-muted-foreground leading-relaxed", className)}
        {...props}
    />
));
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription, alertVariants };
