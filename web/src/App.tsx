import { useCallback, useRef, useState } from "react";
import { fetchAnswer, type AnswerResponse, ApiError } from "./api";
import { SearchForm } from "./components/SearchForm";
import { ModeBadge } from "./components/ModeBadge";
import { FilterChips } from "./components/FilterChips";
import { AnswerProse } from "./components/AnswerProse";
import { StatsSummary } from "./components/StatsSummary";
import { ResultsTable } from "./components/ResultsTable";
import { SkeletonResults } from "./components/SkeletonResults";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";

type Status = "idle" | "loading" | "error" | "success";

const EXAMPLES = [
  "moins de 50 000 euros dans le Finistère",
  "nettoyage des locaux d'une mairie",
  "travaux de voirie en Ille-et-Vilaine pour plus de 200 000 euros",
];

export default function App() {
  const [status, setStatus] = useState<Status>("idle");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isWaking, setIsWaking] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const runSearch = useCallback(async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setQuestion(q);
    setStatus("loading");
    setIsWaking(false);
    setErrorMessage(null);

    try {
      const data = await fetchAnswer(trimmed, {
        signal: controller.signal,
        onSlow: () => setIsWaking(true),
      });
      setResult(data);
      setStatus("success");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setErrorMessage(error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.");
      setStatus("error");
    } finally {
      setIsWaking(false);
    }
  }, []);

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-8">
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
            decp copilot
          </h1>
          <p className="mt-1 max-w-2xl text-sm font-light text-ink-muted">
            Recherche hybride sur les marchés publics français attribués depuis 2024 : montants
            comparables, acheteurs, et statistiques chiffrées — pas de conseil juridique, pas de
            prédiction de prix.
          </p>
        </header>

        <SearchForm
          value={question}
          onChange={setQuestion}
          onSubmit={runSearch}
          examples={EXAMPLES}
          disabled={status === "loading"}
        />

        <div className="mt-8">
          {status === "idle" && (
            <p className="text-sm font-light text-ink-faint">
              Essayez une question ci-dessus, ou choisissez un exemple.
            </p>
          )}

          {status === "loading" && <SkeletonResults isWaking={isWaking} />}

          {status === "error" && (
            <ErrorState message={errorMessage} onRetry={() => runSearch(question)} />
          )}

          {status === "success" && result && (
            <div className="flex flex-col gap-5">
              <div className="flex flex-wrap items-center gap-2">
                <ModeBadge mode={result.mode} />
                <FilterChips filters={result.filters} />
              </div>

              {result.answer && <AnswerProse text={result.answer} />}

              {result.markets.length === 0 ? (
                <EmptyState filters={result.filters} />
              ) : (
                <>
                  <StatsSummary stats={result.stats} />
                  <ResultsTable markets={result.markets} />
                </>
              )}
            </div>
          )}
        </div>

        <footer className="mt-16 border-t border-ink-border pt-4 text-xs font-light text-ink-faint">
          Données : data.gouv.fr, Licence Ouverte 2.0 (Etalab) — DECP consolidées, marchés
          notifiés depuis 2024. Aucune clé d'API requise :
          {" "}sans configuration, l'outil restitue déjà les marchés comparables et leurs
          statistiques.
        </footer>
      </div>
    </div>
  );
}
