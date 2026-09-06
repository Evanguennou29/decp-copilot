import type { Market } from "../api";
import { formatDate, formatMontant } from "../format";

interface ResultsTableProps {
  markets: Market[];
}

/** One market per dense row, not a card — comparison is the point, so
 * scanning many results at once matters more than generous spacing. */
export function ResultsTable({ markets }: ResultsTableProps) {
  return (
    <div className="overflow-x-auto border border-ink-border">
      <table className="w-full min-w-[560px] table-fixed border-collapse text-sm">
        <caption className="sr-only">
          Marchés publics correspondant à la recherche, triés par pertinence
        </caption>
        <thead>
          <tr className="border-b border-ink-border text-left text-xs font-medium text-ink-muted">
            <th scope="col" className="w-32 px-3 py-2 text-right">
              Montant
            </th>
            <th scope="col" className="px-3 py-2">
              Marché
            </th>
            <th scope="col" className="hidden w-40 px-3 py-2 sm:table-cell">
              Département
            </th>
            <th scope="col" className="hidden w-24 px-3 py-2 sm:table-cell">
              Date
            </th>
          </tr>
        </thead>
        <tbody>
          {markets.map((market) => (
            <tr
              key={market.uid}
              className="border-b border-ink-border last:border-b-0 hover:bg-paper-raised"
            >
              <td className="tabular-figures whitespace-nowrap px-3 py-2 text-right font-display font-bold text-money">
                {formatMontant(market.montant)}
              </td>
              <td className="px-3 py-2">
                <p className="line-clamp-2 text-ink" title={market.objet}>
                  {market.objet}
                </p>
                <p className="mt-0.5 truncate font-light text-ink-muted">{market.acheteur_nom}</p>
                <p className="mt-0.5 font-light text-ink-faint sm:hidden">
                  {market.departement_nom ?? "département inconnu"} ·{" "}
                  {formatDate(market.date_notification)}
                </p>
              </td>
              <td className="hidden px-3 py-2 font-light text-ink-muted sm:table-cell">
                {market.departement_nom ?? "—"}
              </td>
              <td className="hidden whitespace-nowrap px-3 py-2 font-light text-ink-muted sm:table-cell">
                {formatDate(market.date_notification)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
