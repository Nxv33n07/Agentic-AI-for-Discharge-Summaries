/**
 * GlowPulse — DEPRECATED.
 *
 * Replaced by AnimatedDot (components/ui/animated-dot.tsx). The original used
 * a multi-layered radial gradient + box-shadow ring, which read as the
 * AI-default "neon glow" decoration banned by taste-skill §9.A.
 *
 * Kept as a no-op so existing imports don't break the build. Existing
 * callers (Topbar) have been migrated to AnimatedDot.
 */
export function GlowPulse(_props: Record<string, unknown>): null {
    return null;
}

export default GlowPulse;
