import { useEffect, useState } from 'react';
import { fetchCatalogue } from '../api/catalogue';
import { fetchSkills, type SkillSummary } from '../api/skills';
import { SkillTable } from '../components/SkillTable';
import { describeCatalogueLocation } from '../lib/catalogue';

export function Home() {
  const [status, setStatus] = useState('Asking the API…');
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);

  useEffect(() => {
    const abort = new AbortController();

    fetchCatalogue(abort.signal)
      .then((location) => setStatus(describeCatalogueLocation(location)))
      .catch((error: unknown) => {
        if (!abort.signal.aborted) {
          setStatus(error instanceof Error ? error.message : 'Could not reach the API');
        }
      });

    fetchSkills(abort.signal)
      .then(setSkills)
      .catch((error: unknown) => {
        if (!abort.signal.aborted) {
          setSkillsError(error instanceof Error ? error.message : 'Could not reach the API');
        }
      });

    return () => abort.abort();
  }, []);

  return (
    <main>
      <h1>Skillworks Studio</h1>
      <p data-testid="catalogue-status">{status}</p>
      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && <SkillTable skills={skills} />}
    </main>
  );
}
