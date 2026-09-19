import { describe, expect, it } from 'vitest';
import { chunkedBody } from '../../http/lib/chunkedBody';
import { readLines } from '../../http/lib/lines';
import { foldFilterChoicesLine, type FilterChoicesLine } from './choices';
import { withChosen } from './filters';

async function statesOf(chunks: readonly string[]): Promise<string[][]> {
  const states: string[][] = [];
  let repositories: string[] = [];

  for await (const line of readLines<FilterChoicesLine>(chunkedBody(chunks), new AbortController().signal)) {
    repositories = foldFilterChoicesLine(repositories, line);
    states.push(repositories);
  }

  return states;
}

function wire(...lines: FilterChoicesLine[]): string[] {
  return lines.map((line) => `${JSON.stringify(line)}\n`);
}

const head: FilterChoicesLine = { kind: 'head' };

function day(date: string, repositories: string[]): FilterChoicesLine {
  return { kind: 'day', day: date, repositories };
}

const end: FilterChoicesLine = { kind: 'end' };

describe('foldFilterChoicesLine', () => {
  it('grows the list as each day lands, each repository once and in order', async () => {
    const states = await statesOf(
      wire(
        head,
        day('2026-09-15', ['acme/xi']),
        day('2026-09-14', ['acme/nu', 'acme/xi']),
        day('2026-09-13', []),
        end,
      ),
    );

    expect(states).toEqual([
      [],
      ['acme/xi'],
      ['acme/nu', 'acme/xi'],
      ['acme/nu', 'acme/xi'],
      ['acme/nu', 'acme/xi'],
    ]);
  });

  it('orders the list as the API orders a day, ignoring case', async () => {
    const states = await statesOf(wire(head, day('2026-09-15', ['Globex/xi', 'acme/a_b']), day('2026-09-14', ['acme/ab'])));

    expect(states.at(-1)).toEqual(['acme/ab', 'acme/a_b', 'Globex/xi']);
  });

  it('keeps a picked repository in the list while no day that lands names it', async () => {
    const states = await statesOf(wire(head, day('2026-09-15', ['acme/xi']), day('2026-09-14', []), end));

    expect(states.map((repositories) => withChosen(repositories, 'acme/gone'))).toEqual([
      ['acme/gone'],
      ['acme/gone', 'acme/xi'],
      ['acme/gone', 'acme/xi'],
      ['acme/gone', 'acme/xi'],
    ]);
  });

  it('offers only the repositories of the days that landed when the answer stops early', async () => {
    const states = await statesOf(wire(head, day('2026-09-15', ['acme/xi']), end));

    expect(states.at(-1)).toEqual(['acme/xi']);
  });

  it('lands a day whose line the network split across chunks', async () => {
    const text = wire(head, day('2026-09-15', ['acme/xi']), end).join('');
    const cut = text.indexOf('acme/xi');

    const states = await statesOf([text.slice(0, cut), text.slice(cut)]);

    expect(states).toEqual([[], ['acme/xi'], ['acme/xi']]);
  });
});
