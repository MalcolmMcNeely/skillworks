import { useEffect, useState } from 'react';
import { fetchFilters } from '../api/filters';
import { withChosen } from '../lib/filters';

export function RepositoryPicker({
  repository,
  onChange,
}: {
  repository: string;
  onChange: (repository: string) => void;
}) {
  const [repositories, setRepositories] = useState<string[]>([]);

  useEffect(() => {
    const abort = new AbortController();

    // No message: the choices are a convenience, and the map beside this reports the API's failures.
    fetchFilters(abort.signal).then((choices) => setRepositories(choices.repositories), () => {});

    return () => abort.abort();
  }, []);

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
