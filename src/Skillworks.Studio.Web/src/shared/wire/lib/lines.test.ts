import { describe, expect, it } from 'vitest';
import { chunkedBody } from './chunkedBody';
import { readLines } from './lines';

async function linesOf(body: ReadableStream<Uint8Array>): Promise<unknown[]> {
  const lines: unknown[] = [];

  for await (const line of readLines(body, new AbortController().signal)) {
    lines.push(line);
  }

  return lines;
}

describe('readLines', () => {
  it('reads each line of the body as one JSON value, in the order they came', async () => {
    const body = chunkedBody(['{"kind":"head"}\n{"kind":"day"}\n', '{"kind":"end"}\n']);

    expect(await linesOf(body)).toEqual([{ kind: 'head' }, { kind: 'day' }, { kind: 'end' }]);
  });

  it('puts a line split across chunks back together', async () => {
    const body = chunkedBody(['{"kind":"he', 'ad"}\n{"ki', 'nd":"end"}\n']);

    expect(await linesOf(body)).toEqual([{ kind: 'head' }, { kind: 'end' }]);
  });

  it('puts a character split across chunks back together', async () => {
    const bytes = new TextEncoder().encode('{"name":"✦"}\n');

    const body = chunkedBody([bytes.slice(0, 10), bytes.slice(10)]);

    expect(await linesOf(body)).toEqual([{ name: '✦' }]);
  });

  it('reads a last line that has no line end after it', async () => {
    expect(await linesOf(chunkedBody(['{"kind":"head"}\n{"kind":"end"}']))).toEqual([{ kind: 'head' }, { kind: 'end' }]);
  });

  it('stops reading the body when the signal aborts while it waits for the next line', async () => {
    // Arrange
    const abort = new AbortController();
    let cancelled = false;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"kind":"head"}\n'));
      },
      cancel() {
        cancelled = true;
      },
    });
    const lines = readLines(body, abort.signal);

    // Act
    const first = await lines.next();
    const waiting = lines.next();
    abort.abort();

    // Assert
    expect(first.value).toEqual({ kind: 'head' });
    await expect(waiting).rejects.toMatchObject({ name: 'AbortError' });
    expect(cancelled).toBe(true);
  });
});
