import type { ReactNode } from "react";

interface AnswerProseProps {
  text: string;
}

const HIGHLIGHT_RE = /(\[uid:\s*[^\]]+\])|(\d[\d\s]*\d(?:,\d+)?\s?(?:€|euros?))/gi;

/** Bolds montant figures in the accent colour (the one visual signal
 * reserved for money throughout the app) and mutes citation markers, so a
 * drafted answer still reads with the same visual hierarchy as the table. */
function renderHighlighted(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  HIGHLIGHT_RE.lastIndex = 0;
  while ((match = HIGHLIGHT_RE.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));

    if (match[1]) {
      parts.push(
        <span key={key++} className="text-xs font-light text-ink-faint">
          {match[1]}
        </span>,
      );
    } else {
      parts.push(
        <span key={key++} className="tabular-figures font-bold text-money">
          {match[2]}
        </span>,
      );
    }
    lastIndex = HIGHLIGHT_RE.lastIndex;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export function AnswerProse({ text }: AnswerProseProps) {
  return (
    <blockquote className="border-l-2 border-accent bg-paper-raised py-2 pl-4 text-sm leading-relaxed text-ink">
      {text.split("\n").map((line, index) => (
        <p key={index} className={index > 0 ? "mt-2" : undefined}>
          {renderHighlighted(line)}
        </p>
      ))}
    </blockquote>
  );
}
