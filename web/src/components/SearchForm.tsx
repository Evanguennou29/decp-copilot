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
    <div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor="question" className="block text-xs font-medium text-ink-muted">
            Question sur les marchés publics
          </label>
          <input
            id="question"
            name="question"
            type="text"
            autoComplete="off"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="ex. moins de 50 000 euros dans le Finistère"
            aria-describedby="question-hint"
            className="mt-1 w-full border-0 border-b-2 border-ink-border bg-transparent px-0 py-2
              font-display text-lg text-ink placeholder:text-ink-faint focus:border-accent
              focus:outline-none"
          />
          <p id="question-hint" className="mt-1 text-xs font-light text-ink-faint">
            Montant, département, type de marché, date, ou description libre — vous pouvez
            combiner.
          </p>
        </div>
        <button
          type="submit"
          disabled={disabled}
          className="shrink-0 border-2 border-ink px-5 py-2 font-display text-sm font-bold
            uppercase tracking-wide text-ink transition-colors hover:bg-ink hover:text-paper
            disabled:cursor-wait disabled:opacity-50"
        >
          Chercher
        </button>
      </form>

      <ul className="mt-3 flex flex-wrap gap-2" aria-label="Exemples de questions">
        {examples.map((example) => (
          <li key={example}>
            <button
              type="button"
              onClick={() => {
                onChange(example);
                onSubmit(example);
              }}
              className="border border-ink-border px-2.5 py-1 text-xs font-light text-ink-muted
                transition-colors hover:border-accent hover:text-accent"
            >
              {example}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
