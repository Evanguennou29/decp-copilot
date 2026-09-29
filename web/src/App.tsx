import { useCallback, useEffect, useRef, useState } from "react";
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
  useEffect(() => () => abortRef.current?.abort(), []);

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
        onSlow: () => { if (!controller.signal.aborted) setIsWaking(true); },
      });
      if (controller.signal.aborted) return;
      setResult(data);
      setStatus("success");
    } catch (error) {
      if (controller.signal.aborted) return;
      setErrorMessage(error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.");
      setStatus("error");
    } finally {
      if (abortRef.current === controller) setIsWaking(false);
    }
  }, []);

  return (
    <div className="app-shell min-h-screen">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />
      <div className="relative mx-auto max-w-6xl px-5 pb-10 sm:px-8">
        <header className="site-header flex items-center justify-between gap-4 border-b border-ink-border py-5">
          <a href="#accueil" className="brand flex items-center gap-3" aria-label="DECP Copilot, accueil">
            <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
            <span className="font-display text-sm font-bold tracking-tight sm:text-base">decp<span className="text-money">/</span>copilot</span>
          </a>
          <span className="hidden text-xs text-ink-muted sm:block">L'intelligence des marchés publics</span>
          <a className="header-link text-xs font-medium" href="https://github.com/Evanguennou29/decp-copilot" target="_blank" rel="noreferrer">Voir le projet <span aria-hidden="true">↗</span></a>
        </header>
        <main id="accueil">
          <section className="hero relative pt-16 pb-10 sm:pt-24 sm:pb-14" aria-labelledby="hero-title">
            <div className="hero-orbit" aria-hidden="true"><span /><span /><span /></div>
            <p className="eyebrow mb-5"><span className="status-dot" /> DONNÉES PUBLIQUES · FRANCE</p>
            <h1 id="hero-title" className="hero-title max-w-4xl font-display font-semibold tracking-tight">
              Des marchés comparables.<br /><em>Des décisions éclairées.</em>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-relaxed text-ink-muted sm:text-lg">
              Explorez les marchés publics attribués depuis 2024. Retrouvez leurs montants, leurs acheteurs et leurs territoires, avec des sources vérifiables.
            </p>
          </section>
          <section className="search-panel relative z-10" aria-label="Recherche de marchés">
            <div className="panel-topline flex items-center justify-between gap-3"><span>RECHERCHE ASSISTÉE</span><span>01 / EXPLORER</span></div>
            <SearchForm value={question} onChange={setQuestion} onSubmit={runSearch} examples={EXAMPLES} disabled={status === "loading"} />
          </section>
          <section className="results-section mt-10 sm:mt-14" aria-label="Résultats" aria-live="polite" aria-busy={status === "loading"}>
            <div className="section-heading mb-5 flex items-end justify-between gap-4">
              <div><p className="eyebrow mb-2">ANALYSE / 02</p><h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">Explorer les résultats</h2></div>
              {status === "success" && result && <span className="result-count tabular-figures">{result.markets.length} marché{result.markets.length > 1 ? "s" : ""}</span>}
            </div>
            {status === "idle" && <div className="idle-state rounded-2xl p-8 sm:p-10">
              <span className="idle-icon" aria-hidden="true">↗</span>
              <p className="mt-5 font-display text-lg font-semibold">Votre recherche commence ici.</p>
              <p className="mt-1 max-w-md text-sm text-ink-muted">Décrivez un type de marché ou combinez un lieu, une période et un montant pour voir les attributions comparables.</p>
            </div>}
            {status === "loading" && <SkeletonResults isWaking={isWaking} />}
            {status === "error" && <ErrorState message={errorMessage} onRetry={() => runSearch(question)} />}
            {status === "success" && result && <div className="result-reveal flex flex-col gap-5" key={question}>
              <div className="flex flex-wrap items-center gap-2"><ModeBadge mode={result.mode} /><FilterChips filters={result.filters} /></div>
              {result.answer && <AnswerProse text={result.answer} />}
              {result.markets.length === 0 ? <EmptyState filters={result.filters} /> : <><StatsSummary stats={result.stats} /><ResultsTable markets={result.markets} /></>}
            </div>}
          </section>
        </main>
        <footer className="site-footer mt-16 flex flex-col gap-3 border-t border-ink-border pt-6 text-xs text-ink-muted sm:flex-row sm:justify-between">
          <span>© DECP Copilot · Marchés attribués depuis 2024</span>
          <span>Données publiques · Licence Ouverte 2.0 · Source : data.gouv.fr</span>
        </footer>
      </div>
    </div>
  );
}
