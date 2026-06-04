import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
    "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:h-5 [&>svg]:w-5",
    {
        variants: {
            variant: {
                default: "bg-card/80 border-primary/20 text-foreground [&>svg]:text-primary",
                info: "border-cyan-300/50 bg-cyan-50/80 text-cyan-900 [&>svg]:text-cyan-600",
                success:
                    "border-emerald-300/50 bg-emerald-50/80 text-emerald-900 [&>svg]:text-emerald-600",
                warning:
                    "border-amber-300/50 bg-amber-50/80 text-amber-900 [&>svg]:text-amber-600",
                danger:
                    "border-red-300/50 bg-red-50/80 text-red-900 [&>svg]:text-red-600",
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
                <div className={icon ? "[&_p]:leading-relaxed" : undefined}>
                    {children}
                </div>
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
        className={cn("mb-1 font-semibold leading-none tracking-tight", className)}
        {...props}
    />
));
AlertTitle.displayName = "AlertTitle";

const AlertDescription = React.forwardRef<
    HTMLParagraphElement,
    React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn("text-sm [&_p]:leading-relaxed", className)}
        {...props}
    />
));
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription, alertVariants };
