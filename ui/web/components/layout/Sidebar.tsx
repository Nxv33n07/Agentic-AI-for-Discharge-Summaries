"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Activity,
    LayoutDashboard,
    Users,
    FileText,
    ShieldCheck,
    Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Sidebar.
 *
 * Design rules followed:
 *  - Single line at desktop (5 nav items, 256px wide), no wrapping.
 *  - Height 100dvh (not h-screen, banned by taste-skill §3.E).
 *  - No decorative colored dot on the active item (banned by §9.F, dots are
 *    reserved for real semantic state). The active state is communicated by:
 *      1) tinted background (bg-primary/10)
 *      2) primary-colored label
 *      3) 2px left accent border (semantic, not decorative)
 *  - Single accent color throughout (the brand cyan).
 *  - No "Agentic AI" tagline micro-meta under the logo (§9.F: "Brand · No. 01"
 *    style sub-eyebrows are banned).
 *  - Footer version stamp kept short and functional.
 */
const NAV_ITEMS = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/patients", label: "Patients", icon: Users },
    { href: "/drafts", label: "Drafts", icon: FileText },
    { href: "/trace", label: "Trace", icon: Activity },
    { href: "/learning", label: "Learning", icon: ShieldCheck },
];

export default function Sidebar() {
    const pathname = usePathname();

    const isActive = (href: string) => {
        if (href === "/") return pathname === "/";
        return pathname === href || pathname.startsWith(href + "/");
    };

    return (
        <aside
            aria-label="Primary"
            data-testid="app-sidebar"
            className="sticky top-0 hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-card min-h-[100dvh]"
        >
            {/* Logo / brand */}
            <Link
                href="/"
                className="flex h-16 items-center gap-3 px-5 border-b border-border focus-visible:outline-none"
                aria-label="Dscribe home"
            >
                <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-input bg-primary text-primary-fg"
                    aria-hidden="true"
                >
                    <Stethoscope className="h-5 w-5" />
                </div>
                <div className="flex flex-col leading-tight">
                    <span className="text-sm font-semibold text-foreground">
                        Dscribe
                    </span>
                </div>
            </Link>

            {/* Primary navigation (one line, single accent) */}
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
                                "group flex items-center gap-3 rounded-input px-3 py-2.5 text-sm font-medium",
                                "transition-colors duration-200",
                                "focus-visible:outline-none",
                                active
                                    ? "bg-primary/10 text-primary border-l-2 border-primary pl-[10px]"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground border-l-2 border-transparent pl-[10px]"
                            )}
                        >
                            <Icon
                                className={cn(
                                    "h-4 w-4 shrink-0",
                                    active
                                        ? "text-primary"
                                        : "text-muted-foreground group-hover:text-foreground"
                                )}
                                aria-hidden="true"
                            />
                            <span className="truncate">{item.label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Footer: short, functional, no decorative copy */}
            <div className="border-t border-border p-4">
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                    v0.1.0 · Preview
                </p>
                <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">
                    Drafts require clinician verification. No clinical
                    content is auto-released.
                </p>
            </div>
        </aside>
    );
}
