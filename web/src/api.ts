export interface Market {
  uid: string;
  acheteur_nom: string;
  objet: string;
  montant: number | null;
  date_notification: string | null;
  departement_nom: string | null;
  score: number;
}

export interface Stats {
  count: number;
  montant_total: number;
  montant_min: number | null;
  montant_max: number | null;
  montant_moyen: number | null;
  montant_median: number | null;
}

export interface Filters {
  montant_min: number | null;
  montant_max: number | null;
  departement_code: string | null;
  date_min: string | null;
  date_max: string | null;
  marche_type: string | null;
  code_cpv: string | null;
}

export interface AnswerResponse {
  mode: "generated" | "degraded";
  answer: string | null;
  markets: Market[];
  stats: Stats;
  filters: Filters;
}

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

export class ApiError extends Error {}

/** How long a request can run before we tell the user the API might be
 * asleep (free-tier hosting spins down after inactivity) — not an error,
 * just a slower-than-usual first request. */
export const WAKE_UP_HINT_DELAY_MS = 4000;

export async function fetchAnswer(
  question: string,
  { signal, onSlow }: { signal?: AbortSignal; onSlow?: () => void } = {},
): Promise<AnswerResponse> {
  const slowTimer = onSlow ? setTimeout(onSlow, WAKE_UP_HINT_DELAY_MS) : undefined;
  try {
    const url = new URL("/answer", API_BASE_URL);
    url.searchParams.set("q", question);
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new ApiError(`L'API a répondu ${response.status}.`);
    }
    return (await response.json()) as AnswerResponse;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      "Impossible de joindre l'API. Elle est peut-être en veille (hébergement gratuit) ou hors ligne.",
    );
  } finally {
    if (slowTimer) clearTimeout(slowTimer);
  }
}
