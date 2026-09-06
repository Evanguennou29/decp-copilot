import type { Filters } from "../api";

interface EmptyStateProps {
  filters: Filters;
}

export function EmptyState({ filters }: EmptyStateProps) {
  const hasFilters =
    filters.montant_min !== null ||
    filters.montant_max !== null ||
    filters.departement_code !== null ||
    filters.date_min !== null ||
    filters.date_max !== null ||
    filters.marche_type !== null ||
    filters.code_cpv !== null;

  return (
    <div className="border border-dashed border-ink-border px-4 py-6 text-center">
      <p className="font-display text-sm font-bold text-ink">Aucun marché ne correspond.</p>
      <p className="mt-1 text-xs font-light text-ink-muted">
        {hasFilters
          ? "Essayez d'élargir le montant, le département ou la période."
          : "Reformulez la question, ou essayez l'un des exemples ci-dessus."}
      </p>
    </div>
  );
}
