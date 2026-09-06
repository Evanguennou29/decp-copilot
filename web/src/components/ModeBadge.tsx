interface ModeBadgeProps {
  mode: "generated" | "degraded";
}

/** Both states are treated as first-class, deliberate modes — not one
 * "real" mode and one apologetic fallback. Degraded is what a fresh clone
 * shows by default (SPEC.md section 1: "un mode nominal documenté"). */
export function ModeBadge({ mode }: ModeBadgeProps) {
  if (mode === "generated") {
    return (
      <span className="inline-flex items-center gap-1.5 border border-accent px-2 py-1 text-xs
        font-medium text-accent">
        <span aria-hidden="true">&#9998;</span>
        Réponse rédigée
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 border border-ink-border px-2 py-1 text-xs
      font-medium text-ink-muted">
      <span aria-hidden="true">&#8942;</span>
      Mode direct — sans clé API
    </span>
  );
}
