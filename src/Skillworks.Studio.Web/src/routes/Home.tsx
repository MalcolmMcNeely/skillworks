import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { fetchCatalogue } from '../api/catalogue';
import { fetchSkills, type SkillSummary } from '../api/skills';
import { FilterBar } from '../components/FilterBar';
import { IngestPanel } from '../components/IngestPanel';
import { SkillTable } from '../components/SkillTable';
import { TelemetrySwitch } from '../components/TelemetrySwitch';
import { describeCatalogueLocation } from '../lib/catalogue';
import { describeFetchFailure } from '../lib/errors';
import { describeEmpty, filterParams, readFilter, type Filter } from '../lib/filters';

export function Home() {
  const [status, setStatus] = useState('Asking the API…');
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [passes, setPasses] = useState(0);

  // The filter lives in the address bar, so a reload, a bookmark and the back button all land on
  // the view the reader built. There is nothing to save and nothing to restore.
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);

  // The same filter written out flat. `params` is a new object on every render, so an effect keyed
  // on it would re-read on every render; keyed on the text, it re-reads when the filter changes.
  const narrowing = params.toString();

  // Counting passes rather than re-reading here keeps this callback the same object for the panel's
  // whole life, so changing a filter cannot tear the ingest poll down and start it again.
  const countPass = useCallback(() => setPasses((counted) => counted + 1), []);

  useEffect(() => {
    const abort = new AbortController();

    fetchCatalogue(abort.signal)
      .then((location) => setStatus(describeCatalogueLocation(location)))
      .catch((failure: unknown) => {
        // An abort is the page tidying up after itself, not a failure worth showing.
        if (!abort.signal.aborted) {
          setStatus(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();
  }, []);

  // Read again when the filter changes and when the ingest finishes a pass, so a session written a
  // moment ago reaches the table without a reload. The table keeps its own sorting across the read.
  useEffect(() => {
    const abort = new AbortController();

    // Read back out of the text rather than closed over from above, so the only thing this effect
    // depends on is the thing it is keyed on.
    fetchSkills(readFilter(new URLSearchParams(narrowing)), abort.signal)
      .then((next) => {
        setSkills(next);
        setSkillsError(null);
      })
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          setSkillsError(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();

    // `passes` is a nudge rather than a value, so nothing above reads it. It is here because a
    // finished pass may have put a new session in the store, and the table should say so.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [narrowing, passes]);

  // Replaced rather than pushed: the address bar holds the view being looked at, and a trip through
  // four filters should not cost four presses of the back button to leave.
  const narrow = (next: Filter) => setParams(filterParams(next), { replace: true });

  return (
    <main>
      <h1>Skillworks Studio</h1>
      <p data-testid="catalogue-status">{status}</p>

      <FilterBar filter={filter} onChange={narrow} />

      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null &&
        (skills.length === 0 ? (
          <p data-testid="skills-empty">{describeEmpty(filter)}</p>
        ) : (
          <SkillTable skills={skills} />
        ))}

      <IngestPanel onPassFinished={countPass} />
      <TelemetrySwitch />
    </main>
  );
}
