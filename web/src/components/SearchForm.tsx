import { type FormEvent } from "react";

interface SearchFormProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  examples: string[];
  disabled: boolean;
}

export function SearchForm({ value, onChange, onSubmit, examples, disabled }: SearchFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(value);
  }

  return (
    <div className="search-content">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor="question" className="block text-xs font-semibold uppercase tracking-widest text-ink-muted">
            Que souhaitez-vous explorer ?
          </label>
          <input
            id="question"
            name="question"
            type="text"
            autoComplete="off"
            maxLength={500}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Ex. Marchés de nettoyage dans le Finistère..."
            aria-describedby="question-hint"
            className="search-input mt-3 w-full rounded-xl border border-ink-border bg-paper-raised px-4 py-4
              font-display text-base text-ink placeholder:text-ink-faint focus:border-accent
              focus:outline-none sm:text-lg"
          />
          <p id="question-hint" className="mt-2 text-xs text-ink-muted">
            Combinez librement montant, département, type de marché et période.
          </p>
        </div>
        <button
          type="submit"
          disabled={disabled}
          className="search-button shrink-0 rounded-xl px-6 py-4 font-display text-sm font-bold
            text-paper transition-colors disabled:cursor-wait disabled:opacity-50"
        >
          Explorer <span aria-hidden="true">↗</span>
        </button>
      </form>

      <ul className="mt-7 flex flex-wrap items-center gap-2" aria-label="Exemples de questions">
        <li className="mr-1 text-xs font-medium text-ink-muted">Suggestions</li>
        {examples.map((example) => (
          <li key={example}>
            <button
              type="button"
              onClick={() => {
                onChange(example);
                onSubmit(example);
              }}
              className="suggestion rounded-full border border-ink-border px-3 py-1.5 text-xs
                text-ink-muted transition-colors hover:border-accent hover:text-accent"
            >
              {example}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
