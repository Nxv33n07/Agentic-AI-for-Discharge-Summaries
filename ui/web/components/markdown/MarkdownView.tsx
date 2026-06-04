/**
 * components/markdown/MarkdownView.tsx
 *
 * Lightweight Markdown renderer for the discharge summary drafts. The agent
 * produces predictable Markdown (headings, paragraphs, lists, bold, inline
 * code, horizontal rules) so we ship a tiny dependency-free parser. It also
 * highlights clinical status markers like [MISSING], [PENDING], [CONFLICT],
 * [NOT DOCUMENTED], [UNCLEAR] as colored chips.
 */

import { cn } from "@/lib/utils";

const AMP = String.fromCharCode(38);
const LT = String.fromCharCode(60);
const GT = String.fromCharCode(62);
const QUOT = String.fromCharCode(34);
const APOS = "&#39;";

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, AMP + "amp;")
        .replace(/</g, LT + "lt;")
        .replace(/>/g, GT + "gt;")
        .replace(/"/g, QUOT + "quot;")
        .replace(/'/g, APOS);
}

function applyInline(text: string): string {
    // Inline code
    text = text.replace(
        /`([^`]+)`/g,
        (_m, code) =>
            `<code class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[0.85em] text-primary">${code}</code>`
    );
    // Bold
    text = text.replace(
        /\*\*([^*]+)\*\*/g,
        (_m, b) => `<strong class="font-semibold text-foreground">${b}</strong>`
    );
    // Italic
    text = text.replace(
        /\*([^*]+)\*/g,
        (_m, i) => `<em>${i}</em>`
    );
    return text;
}

function highlightStatusMarkers(html: string): string {
    // Use a function replacer for the bracketed tokens so that matched content
    // is rendered verbatim. The bracket text is already HTML-escaped earlier
    // (escapeHtml ran before this), so we only need to inject the styling span.
    const wrap = (label: string, cls: string) =>
        `<span class="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[0.78em] ${cls}">${label}</span>`;

    const MISSING_CLS =
        "bg-red-100 text-red-700";
    const PENDING_CLS =
        "bg-amber-100 text-amber-800";
    const CONFLICT_CLS =
        "bg-orange-100 text-orange-800";
    const UNCLEAR_CLS =
        "bg-yellow-100 text-yellow-800";
    const NOT_DOC_CLS =
        "bg-slate-100 text-slate-700";

    // Strip surrounding brackets for the visible label, then show the full
    // bracketed token as a tooltip so clinicians can see the original marker.
    const strip = (s: string) => s.replace(/^\[/, "").replace(/\]$/, "").trim();

    html = html.replace(
        /\[NOT DOCUMENTED\]/g,
        () => wrap("NOT DOCUMENTED", NOT_DOC_CLS)
    );
    html = html.replace(
        /\[PENDING\]/g,
        () => wrap("PENDING", PENDING_CLS)
    );
    html = html.replace(
        /\[MISSING[^\]]*\]/g,
        (m) =>
            `<span title="${m}" class="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[0.78em] ${MISSING_CLS}">${strip(m) || "MISSING"}</span>`
    );
    html = html.replace(
        /\[CONFLICT[^\]]*\]/g,
        (m) =>
            `<span title="${m}" class="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[0.78em] ${CONFLICT_CLS}">${strip(m) || "CONFLICT"}</span>`
    );
    html = html.replace(
        /\[UNCLEAR[^\]]*\]/g,
        (m) =>
            `<span title="${m}" class="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[0.78em] ${UNCLEAR_CLS}">${strip(m) || "UNCLEAR"}</span>`
    );
    return html;
}

function renderMarkdown(md: string): string {
    if (!md) return "";

    const lines = md.replace(/\r\n/g, "\n").split("\n");
    const out: string[] = [];

    let i = 0;
    let inList: "ul" | "ol" | null = null;

    const closeList = () => {
        if (inList) {
            out.push(`</${inList}>`);
            inList = null;
        }
    };

    while (i < lines.length) {
        const line = lines[i];
        const trimmed = line.trim();

        // Horizontal rule
        if (/^---+$/.test(trimmed)) {
            closeList();
            out.push('<hr class="my-6 border-primary/15" />');
            i++;
            continue;
        }

        // Headings
        const h = /^(#{1,6})\s+(.*)$/.exec(trimmed);
        if (h) {
            closeList();
            const level = h[1].length;
            const sizeMap: Record<number, string> = {
                1: "text-2xl font-bold text-primary mt-8 mb-3",
                2: "text-xl font-semibold text-primary mt-6 mb-2",
                3: "text-base font-semibold text-foreground mt-4 mb-2",
                4: "text-sm font-semibold uppercase tracking-wide text-foreground/80 mt-3 mb-1",
                5: "text-sm font-semibold text-foreground/80 mt-2 mb-1",
                6: "text-xs font-semibold uppercase tracking-wider text-foreground/60 mt-2 mb-1",
            };
            const cls = sizeMap[level] ?? sizeMap[3];
            out.push(`<h${level} class="${cls}">${applyInline(escapeHtml(h[2]))}</h${level}>`);
            i++;
            continue;
        }

        // Unordered list
        const ul = /^[-*+]\s+(.*)$/.exec(trimmed);
        if (ul) {
            if (inList !== "ul") {
                closeList();
                out.push('<ul class="ml-5 list-disc space-y-1 text-sm text-foreground/90">');
                inList = "ul";
            }
            out.push(`<li>${applyInline(escapeHtml(ul[1]))}</li>`);
            i++;
            continue;
        }

        // Ordered list
        const ol = /^\d+\.\s+(.*)$/.exec(trimmed);
        if (ol) {
            if (inList !== "ol") {
                closeList();
                out.push('<ol class="ml-5 list-decimal space-y-1 text-sm text-foreground/90">');
                inList = "ol";
            }
            out.push(`<li>${applyInline(escapeHtml(ol[1]))}</li>`);
            i++;
            continue;
        }

        // Blank line
        if (!trimmed) {
            closeList();
            i++;
            continue;
        }

        // Paragraph (collect consecutive non-empty non-special lines)
        closeList();
        const buf: string[] = [trimmed];
        i++;
        while (
            i < lines.length &&
            lines[i].trim() &&
            !/^---+$/.test(lines[i].trim()) &&
            !/^(#{1,6})\s+/.test(lines[i].trim()) &&
            !/^[-*+]\s+/.test(lines[i].trim()) &&
            !/^\d+\.\s+/.test(lines[i].trim())
        ) {
            buf.push(lines[i].trim());
            i++;
        }
        const text = buf.join(" ");
        out.push(
            `<p class="my-2 text-sm leading-relaxed text-foreground/90">${applyInline(escapeHtml(text))}</p>`
        );
    }

    closeList();
    return highlightStatusMarkers(out.join("\n"));
}

export default function MarkdownView({
    content,
    className,
}: {
    content: string;
    className?: string;
}) {
    const html = renderMarkdown(content);
    return (
        <div
            data-testid="draft-output"
            className={cn(
                "prose-custom max-w-none text-foreground",
                "rounded-lg border border-primary/10 bg-card/70 p-5 shadow-sm",
                className
            )}
            dangerouslySetInnerHTML={{ __html: html }}
        />
    );
}
