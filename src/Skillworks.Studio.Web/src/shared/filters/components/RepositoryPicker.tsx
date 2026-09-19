import { useEffect, useState } from 'react';
import { fetchFilterChoices } from '../api/filters';
import { foldFilterChoicesLine } from '../lib/choices';
import { withChosen, type Span } from '../lib/filters';

interface Choices extends Span {
  repositories: string[];
}

export function RepositoryPicker({
  span: { from, to },
  repository,
  onChange,
}: {
  span: Span;
  repository: string;
  onChange: (repository: string) => void;
}) {
  const [choices, setChoices] = useState<Choices | null>(null);

  useEffect(() => {
    const abort = new AbortController();

    const read = async () => {
      const lines = fetchFilterChoices({ from, to }, abort.signal);
      let repositories: string[] = [];

      for await (const line of lines) {
        repositories = foldFilterChoicesLine(repositories, line);
        setChoices({ from, to, repositories });
      }
    };

    // No message: the choices are a convenience, and the map beside this reports the API's failures.
    read().catch(() => undefined);

    // A changed span stops the old answer, so its repositories never land in the new list.
    return () => abort.abort();
  }, [from, to]);

  // An older span's list is not this span's, even when the new answer fails before its first line.
  const repositories = choices?.from === from && choices.to === to ? choices.repositories : [];

  return (
    <label className="picker">
      <span className="picker-glyph" aria-hidden="true">
        ⌥
      </span>
      <span className="visually-hidden">Repository</span>
      <select value={repository} onChange={(event) => onChange(event.target.value)}>
        <option value="">All repositories</option>
        {withChosen(repositories, repository).map((choice) => (
          <option key={choice} value={choice}>
            {choice}
          </option>
        ))}
      </select>
    </label>
  );
}
