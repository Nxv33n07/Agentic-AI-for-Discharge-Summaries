/**
 * ShimmerButton — DEPRECATED.
 *
 * The "shimmer pass" animation reads as the AI-default "shiny button" effect
 * banned by taste-skill §9.A ("NO neon / outer glows by default"). Primary
 * CTAs in Dscribe are now solid fills (see components/ui/button.tsx,
 * variant="cta") with a tactile -translate-y-px on :active.
 *
 * Kept as a no-op so existing imports don't break the build.
 */
export function ShimmerButton(_props: Record<string, unknown>): null {
    return null;
}

export default ShimmerButton;
