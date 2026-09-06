interface ErrorStateProps {
  message: string | null;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="border border-danger bg-danger-soft px-4 py-4">
      <p className="font-display text-sm font-bold text-danger">Recherche impossible.</p>
      <p className="mt-1 text-xs font-light text-ink">
        {message ?? "Une erreur inattendue est survenue."}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 border border-danger px-3 py-1 text-xs font-bold uppercase tracking-wide
          text-danger transition-colors hover:bg-danger hover:text-paper"
      >
        Réessayer
      </button>
    </div>
  );
}
