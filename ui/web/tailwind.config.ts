import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",

        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",
        popover: "var(--popover)",
        "popover-foreground": "var(--popover-foreground)",

        primary: "var(--color-primary)",
        "primary-fg": "var(--color-primary-fg)",
        secondary: "var(--color-secondary)",
        cta: "var(--color-cta)",
        "cta-fg": "var(--color-cta-fg)",
        text: "var(--color-text)",

        "status-missing": "var(--status-missing)",
        "status-pending": "var(--status-pending)",
        "status-conflict": "var(--status-conflict)",
        "status-unclear": "var(--status-unclear)",
        "status-not-documented": "var(--status-not-documented)",
      },
      fontFamily: {
        sans: ["var(--font-fira-sans)", "Fira Sans", "system-ui", "sans-serif"],
        mono: ["var(--font-fira-code)", "Fira Code", "ui-monospace", "monospace"],
      },
      spacing: {
        xs: "var(--space-xs)",
        sm: "var(--space-sm)",
        md: "var(--space-md)",
        lg: "var(--space-lg)",
        xl: "var(--space-xl)",
        "2xl": "var(--space-2xl)",
        "3xl": "var(--space-3xl)",
      },
      borderRadius: {
        input: "var(--radius-input)",
        card: "var(--radius-card)",
        sheet: "var(--radius-sheet)",
        pill: "var(--radius-pill)",
        DEFAULT: "var(--radius-input)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        focus: "var(--shadow-focus)",
      },
      transitionDuration: {
        "200": "200ms",
        "300": "300ms",
      },
    },
  },
  plugins: [],
};
export default config;
