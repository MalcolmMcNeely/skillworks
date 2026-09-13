/**
 * One GET against the API. The status goes in the message, because a 404 on a dev server usually
 * means the proxy is not wired rather than that the data is missing.
 */
export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });

  if (!response.ok) {
    throw new Error(`GET ${path} returned ${response.status}`);
  }

  return (await response.json()) as T;
}

/**
 * One POST against the API. Nothing sent here carries a body: these routes are commands, and what
 * comes back is the state to poll from rather than the answer.
 */
export async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`POST ${path} returned ${response.status}`);
  }

  return (await response.json()) as T;
}

/**
 * One PUT against the API. Studio refuses some writes on purpose, and says why in the problem
 * document, so that reason is the message rather than the status.
 */
export async function putJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as { detail?: string } | null;

    throw new Error(problem?.detail ?? `PUT ${path} returned ${response.status}`);
  }

  return (await response.json()) as T;
}
