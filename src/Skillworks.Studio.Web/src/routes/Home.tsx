import { useEffect, useState } from 'react';
import { fetchCatalogue } from '../api/catalogue';
import { fetchSkills, type SkillSummary } from '../api/skills';
import { SkillTable } from '../components/SkillTable';
import { TelemetrySwitch } from '../components/TelemetrySwitch';
import { describeCatalogueLocation } from '../lib/catalogue';
import { describeFetchFailure } from '../lib/errors';

export function Home() {
  const [status, setStatus] = useState('Asking the API…');
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);

  useEffect(() => {
    const abort = new AbortController();

    // An abort is this effect tidying up after itself, not a failure worth showing.
    const report = (show: (message: string) => void) => (failure: unknown) => {
      if (!abort.signal.aborted) {
        show(describeFetchFailure(failure));
      }
    };

    fetchCatalogue(abort.signal)
      .then((location) => setStatus(describeCatalogueLocation(location)))
      .catch(report(setStatus));

    fetchSkills(abort.signal).then(setSkills).catch(report(setSkillsError));

    return () => abort.abort();
  }, []);

  return (
    <main>
      <h1>Skillworks Studio</h1>
      <p data-testid="catalogue-status">{status}</p>
      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && <SkillTable skills={skills} />}
      <TelemetrySwitch />
    </main>
  );
}
