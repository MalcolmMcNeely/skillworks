import { afterEach, describe, expect, it, vi } from 'vitest';
import { getLines } from './json';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('getLines', () => {
  it('reads the lines of an answer the API gave', async () => {
    vi.stubGlobal('fetch', () => Promise.resolve(new Response('{"kind":"head"}\n{"kind":"end"}\n')));

    const lines: unknown[] = [];

    for await (const line of getLines('/api/skills', new AbortController().signal)) {
      lines.push(line);
    }

    expect(lines).toEqual([{ kind: 'head' }, { kind: 'end' }]);
  });

  it('fails on a status that is not OK before it reads a line', async () => {
    const response = new Response('{"kind":"head"}\n', { status: 502 });
    vi.stubGlobal('fetch', () => Promise.resolve(response));

    await expect(getLines('/api/skills', new AbortController().signal).next()).rejects.toThrow(
      'GET /api/skills returned 502',
    );
    expect(response.bodyUsed).toBe(false);
  });
});
