import { useEffect, useState } from 'react';
import { fetchCatalogue } from '../api/catalogue';
import { describeCatalogueLocation } from '../lib/catalogue';

export function Home() {
  const [status, setStatus] = useState('Asking the API…');

  useEffect(() => {
    const abort = new AbortController();

    fetchCatalogue(abort.signal)
      .then((location) => setStatus(describeCatalogueLocation(location)))
      .catch((error: unknown) => {
        if (!abort.signal.aborted) {
          setStatus(error instanceof Error ? error.message : 'Could not reach the API');
        }
      });

    return () => abort.abort();
  }, []);

  return (
    <main>
      <h1>Skillworks Studio</h1>
      <p data-testid="catalogue-status">{status}</p>
    </main>
  );
}
