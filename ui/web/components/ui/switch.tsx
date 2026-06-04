"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SwitchProps
    extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
    label?: string;
    description?: string;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
    ({ className, label, description, id, ...props }, ref) => {
        const reactId = React.useId();
        const inputId = id ?? reactId;
        return (
            <div className="flex items-start gap-3">
                <label
                    htmlFor={inputId}
                    className="relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus-within:ring-2 focus-within:ring-primary/40 focus-within:ring-offset-2"
                >
                    <input
                        ref={ref}
                        id={inputId}
                        type="checkbox"
                        className="peer sr-only"
                        {...props}
                    />
                    <span
                        aria-hidden="true"
                        className="pointer-events-none block h-5 w-5 rounded-full bg-primary-foreground shadow-md ring-0 transition-transform duration-200 peer-checked:translate-x-5 peer-disabled:opacity-50"
                    />
                    <span
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-0 rounded-full bg-slate-300 transition-colors duration-200 peer-checked:bg-[var(--color-cta)] peer-disabled:opacity-50"
                    />
                </label>
                {(label || description) && (
                    <div className="flex flex-col leading-tight">
                        {label && (
                            <label
                                htmlFor={inputId}
                                className="text-sm font-medium text-foreground cursor-pointer"
                            >
                                {label}
                            </label>
                        )}
                        {description && (
                            <span className="text-xs text-foreground/60">
                                {description}
                            </span>
                        )}
                    </div>
                )}
            </div>
        );
    }
);
Switch.displayName = "Switch";

export { Switch };
