import type { Metadata } from "next";
import { Fira_Code, Fira_Sans } from "next/font/google";
import "./globals.css";
import MainLayout from "@/components/layout/MainLayout";

/**
 * Fonts.
 *
 * Per taste-skill §3.A: use next/font (self-hosted) instead of <link>-based
 * Google Fonts in production. The CSS variables --font-fira-sans and
 * --font-fira-code are referenced in globals.css and tailwind.config.ts.
 */
const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
  variable: "--font-fira-sans",
});

const firaCode = Fira_Code({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-fira-code",
});

export const metadata: Metadata = {
  title: "Dscribe · Discharge Summary Agent",
  description:
    "Agentic AI for safe, clinically-guarded discharge summary drafts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${firaSans.variable} ${firaCode.variable}`}>
      <body className="antialiased">
        {/* Skip-to-content link for keyboard / screen-reader users (a11y). */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-input focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-fg"
        >
          Skip to main content
        </a>
        <MainLayout>{children}</MainLayout>
      </body>
    </html>
  );
}
