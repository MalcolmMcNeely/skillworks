// The status stays in the message: a 404 on a dev server usually means the proxy is not wired.
export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });

  if (!response.ok) {
    throw new Error(`GET ${path} returned ${response.status}`);
  }

  return (await response.json()) as T;
}

// Studio says in the problem document why it refused a write, so that reason is the message.
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
