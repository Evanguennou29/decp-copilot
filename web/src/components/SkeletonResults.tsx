interface SkeletonResultsProps {
  isWaking: boolean;
}

/** Dense skeleton rows matching the real table's row height, so the
 * layout doesn't jump once results arrive. */
export function SkeletonResults({ isWaking }: SkeletonResultsProps) {
  return (
    <div aria-live="polite" aria-busy="true">
      <span className="sr-only">Recherche en cours</span>
      {isWaking && (
        <p className="mb-3 text-xs font-light text-ink-muted">
          L'API se réveille (hébergement gratuit) — cela peut prendre jusqu'à une minute la
          première fois.
        </p>
      )}
      <div className="border border-ink-border">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="flex items-center gap-3 border-b border-ink-border px-3 py-2.5 last:border-b-0"
          >
            <div className="skeleton h-4 w-20 shrink-0" />
            <div className="flex-1">
              <div className="skeleton h-3.5 w-3/4" />
              <div className="skeleton mt-1.5 h-3 w-1/3" />
            </div>
            <div className="skeleton hidden h-3.5 w-24 shrink-0 sm:block" />
          </div>
        ))}
      </div>
    </div>
  );
}
