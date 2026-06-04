"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
    Activity,
    LayoutDashboard,
    Users,
    FileText,
    ShieldCheck,
    ChevronLeft,
    ChevronRight,
    Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";

const NAV_ITEMS = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/patients", label: "Patients", icon: Users },
    { href: "/drafts", label: "Drafts", icon: FileText },
    { href: "/trace", label: "Trace", icon: Activity },
    { href: "/learning", label: "Learning", icon: ShieldCheck },
];

export default function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    const isActive = (href: string) => {
        if (href === "/") return pathname === "/";
        return pathname === href || pathname.startsWith(href + "/");
    };

    return (
        <aside
            aria-label="Primary"
            data-testid="app-sidebar"
            className={cn(
                "sticky top-0 hidden md:flex h-screen flex-col border-r border-primary/10 bg-card transition-[width] duration-300 ease-in-out",
                collapsed ? "w-[72px]" : "w-64"
            )}
        >
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 px-4 border-b border-primary/10">
                <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
                    aria-hidden="true"
                >
                    <Stethoscope className="h-5 w-5" />
                </div>
                {!collapsed && (
                    <div className="flex flex-col leading-tight">
                        <span className="text-sm font-semibold text-primary">
                            Dscribe
                        </span>
                        <span className="text-[10px] uppercase tracking-wider text-foreground/50">
                            Agentic AI
                        </span>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Sidebar">
                {NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            aria-current={active ? "page" : undefined}
                            className={cn(
                                "group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors duration-200",
                                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                                active
                                    ? "bg-primary/10 text-primary"
                                    : "text-foreground/70 hover:bg-primary/5 hover:text-foreground"
                            )}
                        >
                            <Icon
                                className={cn(
                                    "h-4 w-4 shrink-0",
                                    active && "text-primary"
                                )}
                                aria-hidden="true"
                            />
                            {!collapsed && (
                                <span className="truncate">{item.label}</span>
                            )}
                            {active && !collapsed && (
                                <span
                                    aria-hidden="true"
                                    className="ml-auto h-1.5 w-1.5 rounded-full bg-primary"
                                />
                            )}
                        </Link>
                    );
                })}
            </nav>

            <Separator />

            {/* Footer / toggle */}
            <div className="p-3 space-y-3">
                {!collapsed && (
                    <div className="rounded-md bg-primary/5 p-3 text-[11px] leading-relaxed text-foreground/70">
                        <p className="font-semibold text-foreground/80 mb-1">
                            v0.1.0 · Preview
                        </p>
                        <p>
                            All drafts require clinician verification. No clinical
                            content is auto-released.
                        </p>
                    </div>
                )}
                <button
                    type="button"
                    onClick={() => setCollapsed((c) => !c)}
                    aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                    className={cn(
                        "flex w-full items-center gap-2 rounded-md px-3 py-2 text-xs font-medium",
                        "text-foreground/60 hover:bg-primary/5 hover:text-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                        "transition-colors duration-200"
                    )}
                >
                    {collapsed ? (
                        <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    ) : (
                        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                    )}
                    {!collapsed && <span>Collapse</span>}
                </button>
            </div>
        </aside>
    );
}
