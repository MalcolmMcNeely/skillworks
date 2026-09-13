import { useCallback, useEffect, useState } from 'react';
import { fetchCatalogue } from '../api/catalogue';
import { fetchSkills, type SkillSummary } from '../api/skills';
import { IngestPanel } from '../components/IngestPanel';
import { SkillTable } from '../components/SkillTable';
import { TelemetrySwitch } from '../components/TelemetrySwitch';
import { describeCatalogueLocation } from '../lib/catalogue';
import { describeFetchFailure } from '../lib/errors';

export function Home() {
  const [status, setStatus] = useState('Asking the API…');
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);

  // One controller for this page's whole life. The skills are read again on every finished pass, so
  // without it a read started a moment before the page went would still be writing state after it.
  const [abort] = useState(() => new AbortController());

  // Called again every time the ingest finishes a pass, so a session written a moment ago reaches
  // the table without a reload. The table keeps its own sorting across the read.
  const readSkills = useCallback(() => {
    fetchSkills(abort.signal)
      .then(setSkills)
      .catch((failure: unknown) => {
        // An abort is the page tidying up after itself, not a failure worth showing.
        if (!abort.signal.aborted) {
          setSkillsError(describeFetchFailure(failure));
        }
      });
  }, [abort]);

  useEffect(() => {
    fetchCatalogue(abort.signal)
      .then((location) => setStatus(describeCatalogueLocation(location)))
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          setStatus(describeFetchFailure(failure));
        }
      });

    readSkills();

    return () => abort.abort();
  }, [abort, readSkills]);

  return (
    <main>
      <h1>Skillworks Studio</h1>
      <p data-testid="catalogue-status">{status}</p>
      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && <SkillTable skills={skills} />}
      <IngestPanel onPassFinished={readSkills} />
      <TelemetrySwitch />
    </main>
  );
}
