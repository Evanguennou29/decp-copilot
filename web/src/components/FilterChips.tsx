import type { Filters } from "../api";
import { departementLabel, formatDate, formatMontant } from "../format";

interface FilterChipsProps {
  filters: Filters;
}

/** What the app understood from the question, shown back so the user can
 * tell a montant/département filter was actually applied rather than
 * guessed at silently. */
export function FilterChips({ filters }: FilterChipsProps) {
  const chips: string[] = [];

  if (filters.montant_min !== null && filters.montant_max !== null) {
    chips.push(`${formatMontant(filters.montant_min)} – ${formatMontant(filters.montant_max)}`);
  } else if (filters.montant_max !== null) {
    chips.push(`< ${formatMontant(filters.montant_max)}`);
  } else if (filters.montant_min !== null) {
    chips.push(`> ${formatMontant(filters.montant_min)}`);
  }

  if (filters.departement_code) chips.push(departementLabel(filters.departement_code));
  if (filters.marche_type) chips.push(filters.marche_type);
  if (filters.code_cpv) chips.push(`CPV ${filters.code_cpv}`);

  if (filters.date_min && filters.date_max) {
    chips.push(`${formatDate(filters.date_min)} – ${formatDate(filters.date_max)}`);
  } else if (filters.date_min) {
    chips.push(`depuis ${formatDate(filters.date_min)}`);
  }

  if (chips.length === 0) return null;

  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Filtres compris">
      {chips.map((chip) => (
        <li
          key={chip}
          className="tabular-figures border border-accent-soft bg-accent-soft px-2 py-0.5 text-xs
            font-medium text-accent"
        >
          {chip}
        </li>
      ))}
    </ul>
  );
}
