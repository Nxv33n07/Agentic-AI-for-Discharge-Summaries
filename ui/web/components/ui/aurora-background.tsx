/**
 * AuroraBackground — DEPRECATED.
 *
 * The taste-skill anti-slop audit (Leonxlnx/taste-skill §4 + §5) flagged this
 * component as a "deep space violet aurora" — exactly the AI-default decoration
 * the skill warns against for clinical / product surfaces. The new app shell
 * background lives in globals.css as `.app-shell-bg` (a calm radial wash on
 * the light theme, no animation, no glassmorphism).
 *
 * This module is kept as a no-op so existing imports don't break the build.
 * Remove the imports from any page that references it.
 */
export function AuroraBackground(_props: Record<string, unknown>): null {
    return null;
}

export default AuroraBackground;
