/**
 * One GET against the API. The status goes in the message, because a 404 on a dev server usually
 * means the proxy is not wired rather than that the data is missing.
 */
export async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });

  if (!response.ok) {
    throw new Error(`GET ${path} returned ${response.status}`);
  }

  return (await response.json()) as T;
}
