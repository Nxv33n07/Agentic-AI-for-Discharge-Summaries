"use client";

import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

/**
 * MainLayout.
 *
 * Design rules followed (taste-skill §3.E + §6):
 *  - min-h-[100dvh] (not h-screen) for iOS Safari address-bar stability.
 *  - Page transition is purposeful (subtle fade + 6px y-shift) and
 *    collapses to instant under prefers-reduced-motion.
 *  - No backdrop-blur, no Aurora, no GridPattern behind the layout.
 *  - The .app-shell-bg utility from globals.css is a calm radial wash
 *    (replaces the previous dark-violet aurora).
 */
export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const reduce = useReducedMotion();

  return (
    <div className="app-shell-bg flex min-h-[100dvh] text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main
          id="main-content"
          role="main"
          className="flex-1 px-4 py-6 md:px-8 md:py-8 max-w-[1400px] w-full mx-auto"
          data-testid="app-root"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={pathname}
              initial={reduce ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -4 }}
              transition={{
                duration: reduce ? 0 : 0.22,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
