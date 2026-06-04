import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> { }

const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, ...props }, ref) => {
        return (
            <input
                type={type}
                className={cn(
                    // Layout: 44px touch target, full-width, comfortable padding
                    "flex h-11 w-full rounded-input border border-input bg-background px-3 py-2",
                    // Type
                    "text-sm text-foreground placeholder:text-muted-foreground",
                    // Motion: only color/border, no transform
                    "transition-colors duration-200",
                    // Focus: handled by :focus-visible in globals.css (box-shadow ring)
                    "focus-visible:outline-none",
                    // Disabled
                    "disabled:cursor-not-allowed disabled:opacity-50",
                    // File input
                    "file:border-0 file:bg-transparent file:text-sm file:font-medium",
                    className
                )}
                ref={ref}
                {...props}
            />
        );
    }
);
Input.displayName = "Input";

export { Input };
