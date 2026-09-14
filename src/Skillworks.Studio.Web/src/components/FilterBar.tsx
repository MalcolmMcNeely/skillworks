import { useEffect, useState } from 'react';
import { fetchFilters, type FilterChoices } from '../api/filters';
import { everything, isEverything, withChosen, type Filter } from '../lib/filters';

const noChoices: FilterChoices = { repositories: [], skills: [] };

export function FilterBar({
  filter,
  onChange,
}: {
  filter: Filter;
  onChange: (filter: Filter) => void;
}) {
  const [choices, setChoices] = useState<FilterChoices>(noChoices);

  useEffect(() => {
    const abort = new AbortController();

    // A failure here is not worth a message. The choices are a convenience; the filter still works
    // typed into the address bar, and the table beside this has its own say about the API.
    fetchFilters(abort.signal).then(setChoices, () => {});

    return () => abort.abort();
  }, []);

  const set = (change: Partial<Filter>) => onChange({ ...filter, ...change });

  return (
    <section className="filters" aria-label="Filters">
      <label>
        From
        <input type="date" value={filter.from} onChange={(e) => set({ from: e.target.value })} />
      </label>

      <label>
        To
        <input type="date" value={filter.to} onChange={(e) => set({ to: e.target.value })} />
      </label>

      <label>
        Repository
        <select
          value={filter.repository}
          onChange={(e) => set({ repository: e.target.value })}
        >
          <option value="">Everywhere</option>
          {withChosen(choices.repositories, filter.repository).map((repository) => (
            <option key={repository} value={repository}>
              {repository}
            </option>
          ))}
        </select>
      </label>

      <label>
        Skill
        <select value={filter.skill} onChange={(e) => set({ skill: e.target.value })}>
          <option value="">Every skill</option>
          {withChosen(choices.skills, filter.skill).map((skill) => (
            <option key={skill} value={skill}>
              {skill}
            </option>
          ))}
        </select>
      </label>

      <button type="button" disabled={isEverything(filter)} onClick={() => onChange(everything)}>
        Clear
      </button>
    </section>
  );
}
