import type { Stats } from "../api";
import { formatMontant } from "../format";

interface StatsSummaryProps {
  stats: Stats;
}

interface Tile {
  label: string;
  value: string;
  isMontant: boolean;
}

/** The primary payoff of the no-key mode: montants, front and centre, bold
 * and in the one accent colour reserved for them — the market count is
 * not a montant, so it stays neutral. */
export function StatsSummary({ stats }: StatsSummaryProps) {
  const tiles: Tile[] = [
    { label: "Marchés", value: String(stats.count), isMontant: false },
    { label: "Total", value: formatMontant(stats.montant_total), isMontant: true },
    { label: "Médian", value: formatMontant(stats.montant_median), isMontant: true },
    { label: "Min", value: formatMontant(stats.montant_min), isMontant: true },
    { label: "Max", value: formatMontant(stats.montant_max), isMontant: true },
  ];

  return (
    <dl className="grid grid-cols-2 gap-px border border-ink-border bg-ink-border sm:grid-cols-5">
      {tiles.map((tile) => (
        <div key={tile.label} className="bg-paper-raised px-3 py-2">
          <dt className="text-xs font-light text-ink-muted">{tile.label}</dt>
          <dd
            className={`tabular-figures font-display text-lg font-bold ${
              tile.isMontant ? "text-money" : "text-ink"
            }`}
          >
            {tile.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
